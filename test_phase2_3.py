from app.db.session import init_db, SessionLocal
from app.db.models import Motorcycle, Invoice, InvoiceItem
from app.services.invoice_service import InvoiceService
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from datetime import datetime

def test_sales_flow():
    print("Initializing DB...")
    init_db()
    db = SessionLocal()
    
    try:
        # 1. Setup Inventory
        chassis = "TEST-CH-001"
        engine = "TEST-ENG-001"
        
        # Cleanup existing
        existing_bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == chassis).first()
        if existing_bike:
            db.delete(existing_bike)
            db.commit()
            
        bike = Motorcycle(
            make="Honda",
            model="CG125",
            year=2024,
            chassis_number=chassis,
            engine_number=engine,
            cost_price=150000,
            sale_price=200000,
            status="IN_STOCK",
            color="Red"
        )
        db.add(bike)
        db.commit()
        db.refresh(bike)
        print(f"Created Bike: {bike.id} - {bike.status}")
        
        # 2. Create Invoice
        item_in = InvoiceItemCreate(
            item_code="123",
            item_name="CG125 Motorcycle",
            quantity=1,
            tax_rate=18.0,
            sale_value=200000,
            chassis_number=chassis,
            engine_number=engine
        )
        
        invoice_in = InvoiceCreate(
            invoice_number=f"INV-{int(datetime.utcnow().timestamp())}",
            datetime=datetime.utcnow(),
            buyer_name="John Doe",
            total_sale_value=200000,
            total_tax_charged=36000,
            total_quantity=1,
            total_amount=236000,
            items=[item_in],
            payment_mode="Cash"
        )
        
        service = InvoiceService()
        # Mock sync_invoice to avoid actual FBR call
        original_sync = service.sync_invoice
        service.sync_invoice = lambda db, inv: print("Mock Sync: Fiscalized")
        
        print("Creating Invoice...")
        invoice = service.create_invoice(db, invoice_in)
        
        # 3. Verify
        db.refresh(bike)
        print(f"Bike Status after Sale: {bike.status}")
        
        if bike.status == "SOLD":
            print("SUCCESS: Bike marked as SOLD.")
        else:
            print("FAILURE: Bike status not updated.")
            
        # Check Link
        item = invoice.items[0]
        if item.motorcycle_id == bike.id:
            print(f"SUCCESS: InvoiceItem linked to Motorcycle ID {bike.id}")
        else:
            print(f"FAILURE: Link missing. Item ID: {item.motorcycle_id}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_sales_flow()
