import pytest
from app.services.captured_data_service import CapturedDataService
from app.db.models import CapturedData, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup in-memory DB for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def service(db_session):
    svc = CapturedDataService()
    svc.db = db_session
    return svc

def test_soft_delete_records(service, db_session):
    # Setup Data
    record1 = CapturedData(name="Rec1", chassis_number="CH-01", is_deleted=False)
    record2 = CapturedData(name="Rec2", chassis_number="CH-02", is_deleted=False)
    db_session.add_all([record1, record2])
    db_session.commit()
    
    # Test Soft Delete
    ids = [record1.id]
    success, msg = service.delete_records(ids, soft_delete=True)
    
    assert success is True
    assert "Soft deleted" in msg
    
    # Verify in DB
    r1 = db_session.query(CapturedData).filter_by(id=record1.id).first()
    r2 = db_session.query(CapturedData).filter_by(id=record2.id).first()
    
    assert r1.is_deleted is True
    assert r2.is_deleted is False

def test_hard_delete_records(service, db_session):
    # Setup Data
    record1 = CapturedData(name="Rec1", chassis_number="CH-01", is_deleted=False)
    db_session.add(record1)
    db_session.commit()
    
    # Test Hard Delete
    ids = [record1.id]
    success, msg = service.delete_records(ids, soft_delete=False)
    
    assert success is True
    assert "Permanently deleted" in msg
    
    # Verify in DB
    r1 = db_session.query(CapturedData).filter_by(id=record1.id).first()
    assert r1 is None

def test_get_captured_data_filters_deleted(service, db_session):
    # Setup Data
    record1 = CapturedData(name="Visible", chassis_number="CH-01", is_deleted=False)
    record2 = CapturedData(name="Hidden", chassis_number="CH-02", is_deleted=True)
    db_session.add_all([record1, record2])
    db_session.commit()
    
    # Test Get
    result = service.get_captured_data()
    data = result["data"]
    
    assert len(data) == 1
    assert data[0].name == "Visible"
