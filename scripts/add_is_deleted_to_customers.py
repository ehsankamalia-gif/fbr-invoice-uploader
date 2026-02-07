import logging
from sqlalchemy import text
from app.db.session import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_is_deleted_to_customers():
    session = SessionLocal()
    try:
        # Check if column exists
        logger.info("Checking if 'is_deleted' column exists in 'customers' table...")
        result = session.execute(text("SHOW COLUMNS FROM customers LIKE 'is_deleted'"))
        if result.fetchone():
            logger.info("'is_deleted' column already exists in 'customers'.")
        else:
            logger.info("Adding 'is_deleted' column to 'customers' table...")
            session.execute(text("ALTER TABLE customers ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            session.commit()
            logger.info("Successfully added 'is_deleted' column to 'customers'.")
            
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_is_deleted_to_customers()
