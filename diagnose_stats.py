import sys
import os
from sqlalchemy import func

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), "fbr_invoice_uploader"))

from app.db.session import SessionLocal, engine
from app.db.models import Motorcycle, Invoice, Customer, CustomerType

def diagnose():
    print(f"Database URL: {engine.url}")
    
    db = SessionLocal()
    try:
        print("\n--- Motorcycle Status Counts ---")
        status_counts = db.query(Motorcycle.status, func.count(Motorcycle.id)).group_by(Motorcycle.status).all()
        for status, count in status_counts:
            print(f"Status '{status}': {count}")
            
        print("\n--- Invoice Stats ---")
        invoice_count = db.query(Invoice).count()
        print(f"Total Invoices: {invoice_count}")
        
        total_sales = db.query(func.sum(Invoice.total_amount)).scalar()
        print(f"Total Sales Amount: {total_sales}")
        
        fbr_success = db.query(Invoice).filter(Invoice.fbr_invoice_number != None).count()
        print(f"FBR Success: {fbr_success}")
        
        fbr_failed = db.query(Invoice).filter(Invoice.sync_status == "FAILED").count()
        print(f"FBR Failed: {fbr_failed}")
        
        print("\n--- Customer Stats ---")
        cust_count = db.query(Customer).filter(Customer.type != CustomerType.DEALER).count()
        print(f"Customers (Non-Dealer): {cust_count}")
        
        dealer_count = db.query(Customer).filter(Customer.type == CustomerType.DEALER).count()
        print(f"Dealers: {dealer_count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
