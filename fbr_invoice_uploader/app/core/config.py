import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

# Determine base directory
if getattr(sys, 'frozen', False):
    # If running as compiled EXE, use the directory of the executable
    BASE_DIR = Path(sys.executable).parent
else:
    # If running as script, use the project root (3 levels up from this file)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Resolve environment-specific FBR settings
CURRENT_FBR_ENV = os.getenv("FBR_ENV", "SANDBOX").upper()
SANDBOX = {
    "FBR_API_BASE_URL": os.getenv("FBR_SANDBOX_API_BASE_URL", "https://esp.fbr.gov.pk:8243/PT/v1"),
    "FBR_POS_ID": os.getenv("FBR_SANDBOX_POS_ID", os.getenv("FBR_POS_ID", "")),
    "FBR_USIN": os.getenv("FBR_SANDBOX_USIN", os.getenv("FBR_USIN", "")),
    "FBR_AUTH_TOKEN": os.getenv("FBR_SANDBOX_AUTH_TOKEN", os.getenv("FBR_AUTH_TOKEN", "")),
    "FBR_TAX_RATE": os.getenv("FBR_SANDBOX_TAX_RATE", "18.0"),
    "FBR_PCT_CODE": os.getenv("FBR_SANDBOX_PCT_CODE", "8711.2010"),
    "FBR_INVOICE_TYPE": os.getenv("FBR_SANDBOX_INVOICE_TYPE", "Standard"),
    "FBR_DISCOUNT": os.getenv("FBR_SANDBOX_DISCOUNT", "0.0"),
    "FBR_ITEM_CODE": os.getenv("FBR_SANDBOX_ITEM_CODE", ""),
    "FBR_ITEM_NAME": os.getenv("FBR_SANDBOX_ITEM_NAME", ""),
}
PRODUCTION = {
    "FBR_API_BASE_URL": os.getenv("FBR_PROD_API_BASE_URL", "https://esp.fbr.gov.pk:8243/PT/v1"),
    "FBR_POS_ID": os.getenv("FBR_PROD_POS_ID", os.getenv("FBR_POS_ID", "")),
    "FBR_USIN": os.getenv("FBR_PROD_USIN", os.getenv("FBR_USIN", "")),
    "FBR_AUTH_TOKEN": os.getenv("FBR_PROD_AUTH_TOKEN", os.getenv("FBR_AUTH_TOKEN", "")),
    "FBR_TAX_RATE": os.getenv("FBR_PROD_TAX_RATE", "18.0"),
    "FBR_PCT_CODE": os.getenv("FBR_PROD_PCT_CODE", "8711.2010"),
    "FBR_INVOICE_TYPE": os.getenv("FBR_PROD_INVOICE_TYPE", "Standard"),
    "FBR_DISCOUNT": os.getenv("FBR_PROD_DISCOUNT", "0.0"),
    "FBR_ITEM_CODE": os.getenv("FBR_PROD_ITEM_CODE", ""),
    "FBR_ITEM_NAME": os.getenv("FBR_PROD_ITEM_NAME", ""),
}

def _pick_env_value(key: str) -> str:
    selected = SANDBOX if CURRENT_FBR_ENV == "SANDBOX" else PRODUCTION
    return selected.get(key) or os.getenv(key, "")

def get_database_url() -> str:
    """Construct database URL from environment variables."""
    server = os.getenv("DB_SERVER")
    if server:
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "fbr_invoice_uploader")
        
        # Encode password to handle special characters
        encoded_password = urllib.parse.quote_plus(password)
        
        return f"mysql+pymysql://{user}:{encoded_password}@{server}:{port}/{name}"
    
    # Ensure forward slashes for SQLite URL to avoid issues on Windows
    return os.getenv("DB_URL", f"sqlite:///{BASE_DIR.as_posix()}/fbr_invoices.db")

class Settings(BaseModel):
    model_config = ConfigDict(case_sensitive=True)

    APP_NAME: str = "FBR Invoice Uploader"
    FBR_ENV: str = Field(default=CURRENT_FBR_ENV)
    FBR_API_BASE_URL: str = Field(default=_pick_env_value("FBR_API_BASE_URL"))
    FBR_POS_ID: str = Field(default=_pick_env_value("FBR_POS_ID"))
    FBR_USIN: str = Field(default=_pick_env_value("FBR_USIN"))
    FBR_AUTH_TOKEN: str = Field(default=_pick_env_value("FBR_AUTH_TOKEN"))
    FBR_TAX_RATE: float = Field(default=float(_pick_env_value("FBR_TAX_RATE") or 18.0))
    FBR_PCT_CODE: str = Field(default=_pick_env_value("FBR_PCT_CODE"))
    
    # New Fields
    FBR_INVOICE_TYPE: str = Field(default=_pick_env_value("FBR_INVOICE_TYPE") or "Standard")
    FBR_DISCOUNT: float = Field(default=float(_pick_env_value("FBR_DISCOUNT") or 0.0))
    FBR_ITEM_CODE: str = Field(default=_pick_env_value("FBR_ITEM_CODE"))
    FBR_ITEM_NAME: str = Field(default=_pick_env_value("FBR_ITEM_NAME"))

    # Ensure forward slashes for SQLite URL to avoid issues on Windows
    DB_URL: str = Field(default_factory=get_database_url)
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    ENCRYPTION_KEY: str = Field(default=os.getenv("ENCRYPTION_KEY", ""))
    HONDA_PORTAL_USERNAME: str = Field(default=os.getenv("HONDA_PORTAL_USERNAME", ""))
    HONDA_PORTAL_PASSWORD: str = Field(default=os.getenv("HONDA_PORTAL_PASSWORD", ""))

settings = Settings()

def reload_settings():
    """Reload settings from .env and re-apply environment selection."""
    load_dotenv(dotenv_path=env_path, override=True)
    global CURRENT_FBR_ENV, SANDBOX, PRODUCTION, settings
    CURRENT_FBR_ENV = os.getenv("FBR_ENV", "SANDBOX").upper()
    SANDBOX = {
        "FBR_API_BASE_URL": os.getenv("FBR_SANDBOX_API_BASE_URL", "https://esp.fbr.gov.pk:8243/PT/v1"),
        "FBR_POS_ID": os.getenv("FBR_SANDBOX_POS_ID", os.getenv("FBR_POS_ID", "")),
        "FBR_USIN": os.getenv("FBR_SANDBOX_USIN", os.getenv("FBR_USIN", "")),
        "FBR_AUTH_TOKEN": os.getenv("FBR_SANDBOX_AUTH_TOKEN", os.getenv("FBR_AUTH_TOKEN", "")),
        "FBR_TAX_RATE": os.getenv("FBR_SANDBOX_TAX_RATE", "18.0"),
        "FBR_PCT_CODE": os.getenv("FBR_SANDBOX_PCT_CODE", "8711.2010"),
        "FBR_INVOICE_TYPE": os.getenv("FBR_SANDBOX_INVOICE_TYPE", "Standard"),
        "FBR_DISCOUNT": os.getenv("FBR_SANDBOX_DISCOUNT", "0.0"),
        "FBR_ITEM_CODE": os.getenv("FBR_SANDBOX_ITEM_CODE", ""),
        "FBR_ITEM_NAME": os.getenv("FBR_SANDBOX_ITEM_NAME", ""),
    }
    PRODUCTION = {
        "FBR_API_BASE_URL": os.getenv("FBR_PROD_API_BASE_URL", "https://esp.fbr.gov.pk:8243/PT/v1"),
        "FBR_POS_ID": os.getenv("FBR_PROD_POS_ID", os.getenv("FBR_POS_ID", "")),
        "FBR_USIN": os.getenv("FBR_PROD_USIN", os.getenv("FBR_USIN", "")),
        "FBR_AUTH_TOKEN": os.getenv("FBR_PROD_AUTH_TOKEN", os.getenv("FBR_AUTH_TOKEN", "")),
        "FBR_TAX_RATE": os.getenv("FBR_PROD_TAX_RATE", "18.0"),
        "FBR_PCT_CODE": os.getenv("FBR_PROD_PCT_CODE", "8711.2010"),
        "FBR_INVOICE_TYPE": os.getenv("FBR_PROD_INVOICE_TYPE", "Standard"),
        "FBR_DISCOUNT": os.getenv("FBR_PROD_DISCOUNT", "0.0"),
        "FBR_ITEM_CODE": os.getenv("FBR_PROD_ITEM_CODE", ""),
        "FBR_ITEM_NAME": os.getenv("FBR_PROD_ITEM_NAME", ""),
    }
    settings = Settings()
