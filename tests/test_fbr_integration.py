import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Invoice, InvoiceItem, Motorcycle
from app.services.invoice_service import InvoiceService
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from app.core.config import settings

from datetime import datetime

# Setup DB Fixture
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def invoice_service():
    return InvoiceService()

def test_create_invoice_success(db_session, invoice_service):
    """
    Test successful creation: FBR returns success, Data persisted to DB.
    """
    # Prepare Input
    item = InvoiceItemCreate(
        item_code="MOTO-001", 
        item_name="Honda CD70", 
        quantity=1, 
        tax_rate=18.0, 
        sale_value=100000.0,
        tax_charged=18000.0,
        total_amount=118000.0,
        pct_code="87112010"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-2023-001",
        datetime=datetime.now(),
        buyer_name="John Doe",
        buyer_cnic="33303-1234567-1",
        payment_mode="Cash",
        items=[item]
    )

    # Mock FBR Client
    with patch("app.services.invoice_service.fbr_client.post_invoice") as mock_post:
        mock_post.return_value = {
            "InvoiceNumber": "1000000000000001", 
            "Response": "Success", 
            "Code": "100"
        }
        
        # Act
        result = invoice_service.create_invoice(db_session, invoice_in)
        
        # Assert
        assert result.invoice_number == "INV-2023-001"
        assert result.fbr_invoice_number == "1000000000000001"
        assert result.is_fiscalized == True
        
        # Verify DB persistence
        db_inv = db_session.query(Invoice).filter_by(invoice_number="INV-2023-001").first()
        assert db_inv is not None
        assert db_inv.fbr_invoice_number == "1000000000000001"

def test_create_invoice_fbr_failure_no_invoice_number(db_session, invoice_service):
    """
    Test failure: FBR returns success-like response but missing InvoiceNumber (Logical Error).
    DB should NOT have the record.
    """
    item = InvoiceItemCreate(
        item_code="MOTO-001", item_name="Honda CD70", quantity=1, tax_rate=18.0, 
        sale_value=100000.0, tax_charged=18000.0, total_amount=118000.0, pct_code="87112010"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-FAIL-001", items=[item], datetime=datetime.now()
    )

    with patch("app.services.invoice_service.fbr_client.post_invoice") as mock_post:
        # Simulate FBR returning an error message in payload
        mock_post.return_value = {
            "Response": "Invalid Data", 
            "Code": "400"
        }
        
        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            invoice_service.create_invoice(db_session, invoice_in)
        
        assert "FBR Upload Failed" in str(excinfo.value)
        
        # Verify DB is empty (Rollback worked)
        db_inv = db_session.query(Invoice).filter_by(invoice_number="INV-FAIL-001").first()
        assert db_inv is None

def test_create_invoice_fbr_exception(db_session, invoice_service):
    """
    Test failure: FBR Client raises Exception (Network error, 500, etc).
    DB should NOT have the record.
    """
    item = InvoiceItemCreate(
        item_code="MOTO-001", item_name="Honda CD70", quantity=1, tax_rate=18.0, 
        sale_value=100000.0, tax_charged=18000.0, total_amount=118000.0, pct_code="87112010"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-EXC-001", items=[item], datetime=datetime.now()
    )

    with patch("app.services.invoice_service.fbr_client.post_invoice") as mock_post:
        mock_post.side_effect = Exception("Network Timeout")
        
        with pytest.raises(Exception) as excinfo:
            invoice_service.create_invoice(db_session, invoice_in)
            
        assert "Network Timeout" in str(excinfo.value)
        
        db_inv = db_session.query(Invoice).filter_by(invoice_number="INV-EXC-001").first()
        assert db_inv is None

def test_create_invoice_inventory_rollback(db_session, invoice_service):
    """
    Test that Inventory changes (Motorcycle status) are rolled back if FBR fails.
    """
    # Setup Inventory
    bike = Motorcycle(
        chassis_number="CH-123", engine_number="ENG-123", 
        model="CD70", color="Red", status="IN_STOCK",
        cost_price=50000, sale_price=60000, year=2023
    )
    db_session.add(bike)
    db_session.commit()
    
    # Prepare Invoice
    item = InvoiceItemCreate(
        item_code="MOTO-001", item_name="Honda CD70", quantity=1, tax_rate=18.0, 
        sale_value=100000.0, tax_charged=18000.0, total_amount=118000.0, pct_code="87112010",
        chassis_number="CH-123", engine_number="ENG-123"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-ROLLBACK-001", items=[item], datetime=datetime.now()
    )
    
    with patch("app.services.invoice_service.fbr_client.post_invoice") as mock_post:
        mock_post.side_effect = Exception("FBR Down")
        
        with pytest.raises(Exception):
            invoice_service.create_invoice(db_session, invoice_in)
            
        # Verify Bike is still IN_STOCK (Rollback successful)
        db_session.refresh(bike)
        assert bike.status == "IN_STOCK"

def test_create_invoice_fbr_echo_failure(db_session, invoice_service):
    """
    Simulate scenario where FBR returns the input InvoiceNumber (echo) 
    but the Response indicates failure or it's just an echo.
    The system should NOT save this.
    """
    # Input Data
    item = InvoiceItemCreate(
        item_code="MOTO-001", item_name="Honda CD70", quantity=1, tax_rate=18.0, 
        sale_value=100000.0, tax_charged=18000.0, total_amount=118000.0, pct_code="87112010"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-ECHO-TEST", 
        datetime=datetime.now(),
        buyer_name="John Doe", buyer_cnic="33303-1234567-1", payment_mode="Cash",
        items=[item]
    )

    # Mock FBR Client to return the input InvoiceNumber (Echo)
    mock_response = {
        "InvoiceNumber": "INV-ECHO-TEST", # Echoed ID, NOT a valid FBR ID
        "Response": "Invalid Headers",
        "Code": "403"
    }

    with patch("app.services.invoice_service.fbr_client.post_invoice", return_value=mock_response):
        try:
            invoice_service.create_invoice(db_session, invoice_in)
            pytest.fail("Invoice was saved despite FBR failure (Echoed ID)")
        except Exception as e:
            # Expected behavior: Exception raised, rollback called
            assert "FBR Validation Failed" in str(e) or "FBR Upload Failed" in str(e)
            
            # Verify DB is empty
        db_inv = db_session.query(Invoice).filter_by(invoice_number="INV-ECHO-TEST").first()
        assert db_inv is None

def test_create_invoice_success_alphanumeric(db_session, invoice_service):
    """
    Test successful creation with ALPHANUMERIC FBR Invoice Number.
    """
    # Prepare Input
    item = InvoiceItemCreate(
        item_code="MOTO-001", item_name="Honda CD70", quantity=1, tax_rate=18.0, 
        sale_value=100000.0, tax_charged=18000.0, total_amount=118000.0, pct_code="87112010"
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-ALPHA-001", 
        datetime=datetime.now(),
        buyer_name="John Doe", buyer_cnic="33303-1234567-1", payment_mode="Cash",
        items=[item]
    )

    # Mock FBR Client with alphanumeric ID
    with patch("app.services.invoice_service.fbr_client.post_invoice") as mock_post:
        mock_post.return_value = {
            "InvoiceNumber": "966416FA2N32258532*test*", 
            "Response": "Success", 
            "Code": "100"
        }
        
        # Act
        result = invoice_service.create_invoice(db_session, invoice_in)
        
        # Assert
        assert result.invoice_number == "INV-ALPHA-001"
        assert result.fbr_invoice_number == "966416FA2N32258532*test*"
        assert result.is_fiscalized == True
