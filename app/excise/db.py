from app.db.session import engine
from app.excise.models import ExciseBase

def init_excise_db():
    """Initializes the Excise & Taxation module tables."""
    ExciseBase.metadata.create_all(bind=engine)
