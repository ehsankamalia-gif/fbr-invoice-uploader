from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.core import config
from app.db.models import Base
import logging

logger = logging.getLogger(__name__)

# Configure connect_args based on DB type
connect_args = {}
if "sqlite" in config.settings.DB_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    config.settings.DB_URL, 
    connect_args=connect_args,
    pool_pre_ping=True # Helps with MySQL connection drops
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Re-initialize the database engine. Useful after settings change."""
    global engine, SessionLocal
    
    # Configure connect_args based on DB type
    connect_args = {}
    if "sqlite" in config.settings.DB_URL:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        config.settings.DB_URL, 
        connect_args=connect_args,
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_connection():
    """Check if the database connection is working."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB Connection check failed: {e}")
        return False

def create_mysql_db_if_missing():
    """
    Checks if the MySQL database exists, and creates it if not.
    This requires parsing the DB_URL to connect to the server without a DB first.
    """
    if "mysql" not in config.settings.DB_URL:
        return

    try:
        # Try connecting normally
        with engine.connect() as conn:
            pass
    except OperationalError as e:
        if "Unknown database" in str(e):
            logger.info("Database does not exist. Attempting to create it...")
            # Parse URL to get base connection string (remove DB name)
            # Assumption: DB_URL format is mysql+pymysql://user:pass@host:port/dbname
            try:
                from sqlalchemy.engine.url import make_url
                url = make_url(config.settings.DB_URL)
                db_name = url.database
                
                # Create a URL without the database name to connect to the server
                # We can't modify the url object directly easily in all versions, 
                # but we can replace the database component
                server_url = url.set(database="")
                
                # Create temporary engine
                tmp_engine = create_engine(server_url)
                with tmp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
                    logger.info(f"Database '{db_name}' created successfully.")
            except Exception as create_error:
                logger.error(f"Failed to create database: {create_error}")
                # Re-raise original error if creation fails
                raise e
        else:
            raise e

def run_migrations():
    """
    Manual migrations to ensure DB schema is up to date.
    """
    try:
        with engine.connect() as conn:
            # Check if total_further_tax column exists in invoices
            try:
                # Attempt to select the column. If it fails, it doesn't exist.
                conn.execute(text("SELECT total_further_tax FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding total_further_tax to invoices table.")
                # Handle SQLite vs MySQL syntax if needed, but ADD COLUMN is standard
                conn.execute(text("ALTER TABLE invoices ADD COLUMN total_further_tax FLOAT DEFAULT 0.0"))
                conn.commit()
                
            # Check if further_tax column exists in invoice_items
            try:
                 conn.execute(text("SELECT further_tax FROM invoice_items LIMIT 1"))
            except Exception:
                 logger.info("Migrating: Adding further_tax to invoice_items table.")
                 conn.execute(text("ALTER TABLE invoice_items ADD COLUMN further_tax FLOAT DEFAULT 0.0"))
                 conn.commit()

    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        print(f"Migration check failed: {e}") # Ensure visibility in console

    # Additional migrations for product_model_id and fbr_configurations
    try:
        with engine.connect() as conn:
            # Check for product_model_id in motorcycles
            try:
                conn.execute(text("SELECT product_model_id FROM motorcycles LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding product_model_id to motorcycles table.")
                # SQLite supports ADD COLUMN. Note: Constraints might not be enforced immediately depending on version/pragma
                conn.execute(text("ALTER TABLE motorcycles ADD COLUMN product_model_id INTEGER DEFAULT 1")) 
                conn.commit()
            
            # Check for customer_id in invoices
            try:
                conn.execute(text("SELECT customer_id FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding customer_id to invoices table.")
                conn.execute(text("ALTER TABLE invoices ADD COLUMN customer_id INTEGER DEFAULT NULL"))
                conn.commit()

            # Check for fbr_full_response in invoices
            try:
                conn.execute(text("SELECT fbr_full_response FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding fbr_full_response to invoices table.")
                conn.execute(text("ALTER TABLE invoices ADD COLUMN fbr_full_response TEXT DEFAULT NULL"))
                conn.commit()
            
            # Check for fbr_response_message in invoices
            try:
                conn.execute(text("SELECT fbr_response_message FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding fbr_response_message to invoices table.")
                conn.execute(text("ALTER TABLE invoices ADD COLUMN fbr_response_message TEXT DEFAULT NULL"))
                conn.commit()

            # Check for fbr_response_code in invoices
            try:
                conn.execute(text("SELECT fbr_response_code FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding fbr_response_code to invoices table.")
                conn.execute(text("ALTER TABLE invoices ADD COLUMN fbr_response_code TEXT DEFAULT NULL"))
                conn.commit()

    except Exception as e:
        logger.error(f"Migration phase 2 failed: {e}")


def init_db():
    create_mysql_db_if_missing()
    Base.metadata.create_all(bind=engine)
    run_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
