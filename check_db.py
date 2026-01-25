from app.db.session import SessionLocal
from app.db.models import CapturedData
import sys

def check_last_records():
    db = SessionLocal()
    try:
        records = db.query(CapturedData).order_by(CapturedData.created_at.desc()).limit(5).all()
        print(f"Found {len(records)} records.")
        for r in records:
            print("-" * 50)
            print(f"ID: {r.id}")
            print(f"Name: {r.name}")
            print(f"Father: {r.father}")
            print(f"CNIC: {r.cnic}")
            print(f"Cell: {r.cell}")
            print(f"Address: {r.address}")
            print(f"Chassis: {r.chassis_number}")
            print(f"Engine: {r.engine_number}")
            print(f"Created: {r.created_at}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_last_records()
