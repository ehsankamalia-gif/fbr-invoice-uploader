from app.db.session import SessionLocal
from sqlalchemy import text

def add_column():
    session = SessionLocal()
    try:
        # Check if column exists by trying to select it
        try:
            session.execute(text("SELECT status_updated_at FROM invoices LIMIT 1"))
            print("Column status_updated_at already exists.")
        except Exception:
            print("Adding status_updated_at column to invoices table...")
            # MySQL syntax
            session.execute(text("ALTER TABLE invoices ADD COLUMN status_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            session.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_column()
