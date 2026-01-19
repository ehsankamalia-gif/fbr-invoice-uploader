from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.core.config import settings
from app.db.models import Base
import logging

logger = logging.getLogger(__name__)

# Configure connect_args based on DB type
connect_args = {}
if "sqlite" in settings.DB_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DB_URL, 
    connect_args=connect_args,
    pool_pre_ping=True # Helps with MySQL connection drops
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_mysql_db_if_missing():
    """
    Checks if the MySQL database exists, and creates it if not.
    This requires parsing the DB_URL to connect to the server without a DB first.
    """
    if "mysql" not in settings.DB_URL:
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
                url = make_url(settings.DB_URL)
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
