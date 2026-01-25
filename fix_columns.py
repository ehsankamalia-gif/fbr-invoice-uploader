import pymysql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_columns():
    conn = pymysql.connect(host='127.0.0.1', user='root', password='', db='honda_fbr')
    cursor = conn.cursor()
    
    try:
        # Check if model_id exists in motorcycles
        cursor.execute("SHOW COLUMNS FROM motorcycles LIKE 'model_id'")
        if cursor.fetchone():
            logger.info("Renaming motorcycles.model_id to product_model_id...")
            # Drop FK first? MySQL can rename column with FK usually, but let's be safe.
            # Actually, CHANGE COLUMN can handle it.
            cursor.execute("ALTER TABLE motorcycles CHANGE COLUMN model_id product_model_id INT")
            # FK name might be fk_motorcycle_model. Ideally we rename it too but it's not strictly required.

        # Check if model_id exists in prices
        cursor.execute("SHOW COLUMNS FROM prices LIKE 'model_id'")
        if cursor.fetchone():
            logger.info("Renaming prices.model_id to product_model_id...")
            cursor.execute("ALTER TABLE prices CHANGE COLUMN model_id product_model_id INT")

        conn.commit()
        logger.info("Fix complete.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Fix failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_columns()
