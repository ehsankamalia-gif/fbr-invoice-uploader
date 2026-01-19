import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.invoice_service import InvoiceService
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from app.db.models import Invoice, InvoiceItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base

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
def sample_invoice_data():
    return InvoiceCreate(
        invoice_number="INV-TEST-001",
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
                further_tax=2000.0,
                pct_code="8711.2010",
                chassis_number="CH-001",
                engine_number="ENG-001",
                discount=0.0
            )
        ]
    )

@patch("app.services.invoice_service.fbr_client.post_invoice")
@patch("app.services.settings_service.settings_service.get_active_settings")
def test_create_invoice_success_db_settings(mock_get_active_settings, mock_post_invoice, db, invoice_service, sample_invoice_data):
    # 1. Setup Mock Settings
    mock_get_active_settings.return_value = {
        "env": "SANDBOX",
        "api_base_url": "https://test.fbr.gov.pk",
        "pos_id": "POS-123",
        "usin": "USIN-TEST",
        "auth_token": "TOKEN-123",
        "tax_rate": 18.0
    }

    # 2. Setup Mock FBR Response (Success)
    mock_post_invoice.return_value = {
        "InvoiceNumber": "123456789012345678",
        "Response": "Success",
        "Code": "100"
    }

    # 3. Call Service
    result = invoice_service.create_invoice(db, sample_invoice_data)

    # 4. Assertions
    # Verify settings were fetched
    mock_get_active_settings.assert_called()
    
    # Verify FBR Client was called
    mock_post_invoice.assert_called_once()
    
    # Verify DB persistence
    saved_invoice = db.query(Invoice).filter_by(invoice_number="INV-TEST-001").first()
    assert saved_invoice is not None
    assert saved_invoice.is_fiscalized == True
    assert saved_invoice.fbr_invoice_number == "123456789012345678"
    assert saved_invoice.pos_id == "POS-123"  # Should come from settings

@patch("app.services.invoice_service.fbr_client.post_invoice")
@patch("app.services.settings_service.settings_service.get_active_settings")
def test_create_invoice_failure_rollback(mock_get_active_settings, mock_post_invoice, db, invoice_service, sample_invoice_data):
    # 1. Setup Mock Settings
    mock_get_active_settings.return_value = {
        "env": "SANDBOX",
        "pos_id": "POS-123"
    }

    # 2. Setup Mock FBR Response (Failure/Empty)
    mock_post_invoice.return_value = {} # Empty response triggers error

    # 3. Call Service and Expect Error
    with pytest.raises(ValueError, match="Received empty response from FBR"):
        invoice_service.create_invoice(db, sample_invoice_data)

    # 4. Assertions
    # Verify DB Rollback (Invoice should NOT be in DB)
    saved_invoice = db.query(Invoice).filter_by(invoice_number="INV-TEST-001").first()
    assert saved_invoice is None

@patch("app.services.invoice_service.fbr_client.post_invoice")
@patch("app.services.settings_service.settings_service.get_active_settings")
def test_create_invoice_echo_error_rollback(mock_get_active_settings, mock_post_invoice, db, invoice_service, sample_invoice_data):
    # 1. Setup Mock Settings
    mock_get_active_settings.return_value = {"pos_id": "POS-123"}

    # 2. Setup Mock FBR Response (Echo Error)
    mock_post_invoice.return_value = {
        "InvoiceNumber": "INV-TEST-001", # Echoed invoice number
        "Response": "Success"
    }

    # 3. Call Service and Expect Error
    with pytest.raises(Exception, match="FBR returned echoed Invoice Number"):
        invoice_service.create_invoice(db, sample_invoice_data)

    # 4. Verify DB Rollback
    saved_invoice = db.query(Invoice).filter_by(invoice_number="INV-TEST-001").first()
    assert saved_invoice is None
