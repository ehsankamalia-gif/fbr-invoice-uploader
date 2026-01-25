from app.db.session import init_db, SessionLocal
from app.db.models import Motorcycle, Supplier, ProductModel

def test_inventory():
    print("Initializing DB...")
    init_db()
    
    db = SessionLocal()
    try:
        # Create Supplier
        supplier = Supplier(name="Atlas Honda", contact_person="Ali", phone="03001234567")
        db.add(supplier)
        
        # Create ProductModel
        pm = db.query(ProductModel).filter(ProductModel.model_name == "CD70").first()
        if not pm:
            pm = ProductModel(model_name="CD70", make="Honda", engine_capacity="70cc")
            db.add(pm)
            db.commit()
            
        # Cleanup existing bike if any
        existing_bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == "CH12345").first()
        if existing_bike:
            db.delete(existing_bike)
            db.commit()
        
        # Create Motorcycle
        bike = Motorcycle(
            product_model=pm,
            year=2025,
            chassis_number="CH12345",
            engine_number="ENG12345",
            cost_price=100000,
            sale_price=150000,
            supplier=supplier
        )
        db.add(bike)
        db.commit()
        
        print(f"Added Bike: {bike.model} with ID: {bike.id}")
        
        # Query
        count = db.query(Motorcycle).count()
        print(f"Total Bikes: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_inventory()
