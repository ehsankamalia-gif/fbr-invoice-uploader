import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.invoice_service import InvoiceService
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from app.db.models import Invoice, InvoiceItem, CapturedData, Motorcycle, ProductModel, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup in-memory DB for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def invoice_service():
    return InvoiceService()

@pytest.fixture
def setup_inventory(db):
    # Create Product Model
    pm = ProductModel(model_name="CD70", make="Honda", engine_capacity="70cc")
    db.add(pm)
    db.commit()
    db.refresh(pm)
    
    # Create Motorcycle
    bike = Motorcycle(
        chassis_number="CH-001",
        engine_number="ENG-001",
        product_model_id=pm.id,
        year=2024,
        color="RED",
        cost_price=50000,
        sale_price=100000,
        status="IN_STOCK"
    )
    db.add(bike)
    
    # Create Captured Data Record
    cd = CapturedData(
        chassis_number="CH-001",
        engine_number="ENG-001",
        name="Test User",
        cnic="12345-1234567-1"
    )
    db.add(cd)
    db.commit()
    return bike

@pytest.fixture
def sample_invoice_data():
    return InvoiceCreate(
        invoice_number="INV-TEST-DEL-001",
        datetime=datetime.now(),
        buyer_name="John Doe",
        buyer_ntn="1234567-8",
        buyer_cnic="33302-1234567-0",
        buyer_phone="03001234567",
        buyer_address="Test Address",
        payment_mode="Cash",
        items=[
            InvoiceItemCreate(
                item_code="MOTO-001",
                item_name="Honda CD70",
                quantity=1,
                tax_rate=18.0,
                sale_value=100000.0,
                tax_charged=18000.0,
                further_tax=0.0,
                pct_code="8711.2010",
                chassis_number="CH-001",
                engine_number="ENG-001",
                discount=0.0
            )
        ]
    )

@patch("app.services.invoice_service.fbr_client.post_invoice")
@patch("app.services.settings_service.settings_service.get_active_settings")
def test_auto_delete_captured_data_on_success(mock_get_active_settings, mock_post_invoice, db, invoice_service, setup_inventory, sample_invoice_data):
    # 1. Setup Mock Settings
    mock_get_active_settings.return_value = {
        "env": "SANDBOX",
        "api_base_url": "https://test.fbr.gov.pk",
        "pos_id": "POS-123",
        "usin": "USIN-TEST",
        "auth_token": "TOKEN-123"
    }

    # 2. Setup Mock FBR Response (Success)
    mock_post_invoice.return_value = {
        "InvoiceNumber": "123456789012345678",
        "Response": "Success",
        "Code": "100"
    }

    # 3. Verify Pre-condition: Captured Data Exists
    cd_before = db.query(CapturedData).filter_by(chassis_number="CH-001").first()
    assert cd_before is not None

    # 4. Call Service
    result = invoice_service.create_invoice(db, sample_invoice_data)

    # 5. Assertions
    # Verify FBR Client was called
    mock_post_invoice.assert_called_once()
    
    # Verify Invoice Created and Synced
    assert result.sync_status == "SYNCED"
    
    # Verify Captured Data is DELETED
    cd_after = db.query(CapturedData).filter_by(chassis_number="CH-001").first()
    assert cd_after is None

@patch("app.services.invoice_service.fbr_client.post_invoice")
@patch("app.services.settings_service.settings_service.get_active_settings")
def test_no_delete_on_failure(mock_get_active_settings, mock_post_invoice, db, invoice_service, setup_inventory, sample_invoice_data):
    # 1. Setup Mock Settings
    mock_get_active_settings.return_value = {
        "env": "SANDBOX",
        "pos_id": "POS-123"
    }

    # 2. Setup Mock FBR Response (Failure)
    mock_post_invoice.return_value = {
        "Response": "Invalid Invoice",
        "Code": "400"
    }

    # 3. Call Service (This might raise exception or return invoice with FAILED status depending on implementation)
    # create_invoice raises exception on failure in the "try" block if DB rollback happens, 
    # OR returns invoice if it was saved locally (offline mode).
    # In invoice_service.py:
    # if str(fbr_code) != "100": raise Exception...
    # Then caught in except block. If db_invoice in db, commit and return.
    
    try:
        result = invoice_service.create_invoice(db, sample_invoice_data)
    except Exception:
        pass # Expected failure

    # 4. Verify Captured Data STILL EXISTS
    cd_after = db.query(CapturedData).filter_by(chassis_number="CH-001").first()
    assert cd_after is not None
