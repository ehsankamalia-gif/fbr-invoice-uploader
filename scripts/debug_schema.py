import logging
from sqlalchemy import text
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_schema():
    session = SessionLocal()
    try:
        # Check DB Schema
        result = session.execute(text("SHOW COLUMNS FROM captured_data"))
        columns = [row[0] for row in result]
        logger.info(f"DB Columns: {columns}")
        
        if 'is_deleted' in columns:
            logger.info("is_deleted column exists in DB.")
        else:
            logger.error("is_deleted column MISSING in DB.")

        # Check Model Definition
        from app.db.models import CapturedData
        if hasattr(CapturedData, 'is_deleted'):
            logger.info("CapturedData model has is_deleted attribute.")
        else:
            logger.error("CapturedData model MISSING is_deleted attribute.")

        # Check data
        count_deleted = session.query(CapturedData).filter(text("is_deleted = 1")).count()
        count_active = session.query(CapturedData).filter(text("is_deleted = 0")).count()
        logger.info(f"Data stats: Active={count_active}, Deleted={count_deleted}")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_schema()
