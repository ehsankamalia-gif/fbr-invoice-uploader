import pytest
from unittest.mock import MagicMock
from app.services.invoice_service import InvoiceService
from app.db.models import Invoice, InvoiceItem, Motorcycle, Base, ProductModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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

def test_is_chassis_used_in_posted_invoice_empty(db, invoice_service):
    """Test with empty DB"""
    assert invoice_service.is_chassis_used_in_posted_invoice(db, "CH-001") is False

def test_is_chassis_used_in_posted_invoice_found(db, invoice_service):
    """Test when chassis is present in a posted invoice"""
    # Create ProductModel
    model = ProductModel(model_name="CG125", make="Honda")
    db.add(model)
    db.flush()

    # Create Invoice
    invoice = Invoice(
        invoice_number="INV-001",
        pos_id="123",
        usin="USIN-1",
        total_sale_value=100.0,
        total_tax_charged=10.0,
        total_quantity=1.0,
        total_amount=110.0,
        is_fiscalized=True # Posted
    )
    db.add(invoice)
    db.flush()

    # Create Motorcycle
    bike = Motorcycle(
        chassis_number="CH-EXISTING",
        engine_number="ENG-001",
        status="SOLD",
        product_model_id=model.id,
        year=2024,
        cost_price=50000.0,
        sale_price=75000.0
    )
    db.add(bike)
    db.flush()

    # Create InvoiceItem linking them
    item = InvoiceItem(
        invoice_id=invoice.id,
        motorcycle_id=bike.id,
        item_code="ITEM-1",
        item_name="Bike",
        quantity=1.0,
        tax_rate=10.0,
        sale_value=100.0,
        tax_charged=10.0,
        total_amount=110.0
    )
    db.add(item)
    db.commit()

    assert invoice_service.is_chassis_used_in_posted_invoice(db, "CH-EXISTING") is True
    assert invoice_service.is_chassis_used_in_posted_invoice(db, "ch-existing") is True # Case insensitive

def test_is_chassis_used_in_posted_invoice_not_found(db, invoice_service):
    """Test when chassis is NOT in any invoice"""
    assert invoice_service.is_chassis_used_in_posted_invoice(db, "CH-NEW") is False

def test_is_chassis_used_in_posted_invoice_null(db, invoice_service):
    """Test with null/empty input"""
    assert invoice_service.is_chassis_used_in_posted_invoice(db, None) is False
    assert invoice_service.is_chassis_used_in_posted_invoice(db, "") is False
