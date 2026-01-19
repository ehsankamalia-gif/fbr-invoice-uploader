import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Invoice
from app.services.invoice_service import InvoiceService
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from unittest.mock import patch

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@patch("app.services.invoice_service.fbr_client.post_invoice")
def test_create_invoice(mock_post, db_session):
    mock_post.return_value = {"InvoiceNumber": "FBR-999"}
    
    service = InvoiceService()
    
    item = InvoiceItemCreate(
        item_code="A1", item_name="Test", quantity=1, tax_rate=10, sale_value=100
    )
    invoice_in = InvoiceCreate(
        invoice_number="INV-TEST",
        items=[item]
    )
    
    invoice = service.create_invoice(db_session, invoice_in)
    
    assert invoice.invoice_number == "INV-TEST"
    assert invoice.total_amount == 110.0
    assert invoice.is_fiscalized == True
    assert invoice.fbr_invoice_number == "FBR-999"
