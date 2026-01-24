import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.models import Base, Motorcycle, Invoice, Customer, CustomerType, ProductModel, Supplier
from app.db.session import get_db

# Test Setup
@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_dashboard_stats_sync(db_session):
    """
    Verifies that dashboard statistics queries accurately reflect the database state.
    """
    # 1. Setup Initial Data
    # Create Product Model
    pm = ProductModel(model_name="CG125", make="Honda", engine_capacity="125cc")
    db_session.add(pm)
    db_session.commit()
    
    # Create Supplier
    sup = Supplier(name="Test Supplier")
    db_session.add(sup)
    db_session.commit()
    
    # Create Motorcycles
    # 2 In Stock
    m1 = Motorcycle(product_model_id=pm.id, chassis_number="CH001", engine_number="EN001", year=2024, cost_price=1000, sale_price=1200, status="IN_STOCK", supplier_id=sup.id)
    m2 = Motorcycle(product_model_id=pm.id, chassis_number="CH002", engine_number="EN002", year=2024, cost_price=1000, sale_price=1200, status="IN_STOCK", supplier_id=sup.id)
    # 1 Sold
    m3 = Motorcycle(product_model_id=pm.id, chassis_number="CH003", engine_number="EN003", year=2024, cost_price=1000, sale_price=1200, status="SOLD", supplier_id=sup.id)
    
    db_session.add_all([m1, m2, m3])
    db_session.commit()
    
    # Create Customers
    c1 = Customer(name="John Doe", type=CustomerType.INDIVIDUAL)
    c2 = Customer(name="Dealer One", type=CustomerType.DEALER)
    db_session.add_all([c1, c2])
    db_session.commit()
    
    # Create Invoices
    # 1 Success
    inv1 = Invoice(invoice_number="INV001", pos_id="123", usin="USIN1", total_sale_value=1000, total_tax_charged=180, total_quantity=1, total_amount=1180, fbr_invoice_number="FBR001", sync_status="Synced")
    # 1 Failed
    inv2 = Invoice(invoice_number="INV002", pos_id="123", usin="USIN1", total_sale_value=1000, total_tax_charged=180, total_quantity=1, total_amount=1180, sync_status="FAILED")
    
    db_session.add_all([inv1, inv2])
    db_session.commit()
    
    # 2. Verify Stats Logic (Mimicking main_window.py)
    
    # Count Motorcycles (In Stock)
    bike_count = db_session.query(Motorcycle).filter(Motorcycle.status == "IN_STOCK").count()
    assert bike_count == 2, f"Expected 2 In Stock, got {bike_count}"
    
    # Count Sold Motorcycles
    sold_count = db_session.query(Motorcycle).filter(Motorcycle.status == "SOLD").count()
    assert sold_count == 1, f"Expected 1 Sold, got {sold_count}"
    
    # Sum Invoices
    invoices = db_session.query(Invoice).all()
    total_sales = sum(inv.total_amount for inv in invoices)
    assert total_sales == 2360, f"Expected 2360 Total Sales, got {total_sales}"
    
    # FBR Success
    fbr_success = db_session.query(Invoice).filter(Invoice.fbr_invoice_number != None).count()
    assert fbr_success == 1, f"Expected 1 FBR Success, got {fbr_success}"

    # FBR Failed
    fbr_failed = db_session.query(Invoice).filter(Invoice.sync_status == "FAILED").count()
    assert fbr_failed == 1, f"Expected 1 FBR Failed, got {fbr_failed}"

    # Customers (Excluding Dealers)
    cust_count = db_session.query(Customer).filter(Customer.type != CustomerType.DEALER).count()
    assert cust_count == 1, f"Expected 1 Customer, got {cust_count}"

    # Dealers
    dealer_count = db_session.query(Customer).filter(Customer.type == CustomerType.DEALER).count()
    assert dealer_count == 1, f"Expected 1 Dealer, got {dealer_count}"
    
    # 3. Modify Data and Verify Updates
    
    # Sell a bike
    m1.status = "SOLD"
    db_session.commit()
    
    bike_count_new = db_session.query(Motorcycle).filter(Motorcycle.status == "IN_STOCK").count()
    sold_count_new = db_session.query(Motorcycle).filter(Motorcycle.status == "SOLD").count()
    
    assert bike_count_new == 1, "In Stock should decrease to 1"
    assert sold_count_new == 2, "Sold should increase to 2"
    
    print("\n✅ Dashboard Synchronization Test Passed!")

if __name__ == "__main__":
    # Manually run the test if executed as script
    try:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        test_dashboard_stats_sync(session)
        session.close()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
