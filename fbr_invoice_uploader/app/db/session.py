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

logger.info(f"Initializing Database with URL: {settings.DB_URL}")

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
                 
            # Check for product_model_id in motorcycles
            try:
                conn.execute(text("SELECT product_model_id FROM motorcycles LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding product_model_id to motorcycles table.")
                
                # Add the column as nullable first
                conn.execute(text("ALTER TABLE motorcycles ADD COLUMN product_model_id INTEGER"))
                conn.commit()
                
                # Populate ProductModels from existing Motorcycles data
                # Find unique models in motorcycles
                try:
                    rows = conn.execute(text("SELECT DISTINCT model, make, engine_capacity FROM motorcycles WHERE model IS NOT NULL")).fetchall()
                    
                    for row in rows:
                        model_name = row[0]
                        make = row[1] or "Honda"
                        capacity = row[2]
                        
                        # Check if exists in product_models
                        pm_check = conn.execute(text("SELECT id FROM product_models WHERE model_name = :m"), {"m": model_name}).fetchone()
                        
                        if pm_check:
                            pm_id = pm_check[0]
                        else:
                            # Insert
                            conn.execute(text("INSERT INTO product_models (model_name, make, engine_capacity) VALUES (:m, :mk, :ec)"), 
                                         {"m": model_name, "mk": make, "ec": capacity})
                            conn.commit()
                            pm_id_row = conn.execute(text("SELECT id FROM product_models WHERE model_name = :m"), {"m": model_name}).fetchone()
                            pm_id = pm_id_row[0]
                        
                        # Update motorcycles
                        conn.execute(text("UPDATE motorcycles SET product_model_id = :pid WHERE model = :m"), {"pid": pm_id, "m": model_name})
                        conn.commit()
                except Exception as ex:
                    logger.error(f"Error migrating motorcycle data: {ex}")
                    # Continue anyway, as the column is added

            # Check for customer_id in invoices
            try:
                conn.execute(text("SELECT customer_id FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding customer_id to invoices table.")
                conn.execute(text("ALTER TABLE invoices ADD COLUMN customer_id INTEGER"))
                conn.commit()

            # Check for fbr_full_response in invoices
            try:
                conn.execute(text("SELECT fbr_full_response FROM invoices LIMIT 1"))
            except Exception:
                logger.info("Migrating: Adding fbr_full_response to invoices table.")
                # SQLite stores JSON as TEXT
                conn.execute(text("ALTER TABLE invoices ADD COLUMN fbr_full_response TEXT"))
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
