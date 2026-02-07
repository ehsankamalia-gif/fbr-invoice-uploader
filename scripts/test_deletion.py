import logging
from app.services.captured_data_service import captured_data_service
from app.db.session import SessionLocal
from app.db.models import CapturedData
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deletion():
    # 1. Check ID 1 status
    session = SessionLocal()
    r = session.query(CapturedData).filter_by(id=1).first()
    if not r:
        logger.error("Record ID 1 not found!")
        return
    logger.info(f"Before delete: ID={r.id}, is_deleted={r.is_deleted}")
    session.close()

    # 2. Perform Soft Delete via Service
    logger.info("Attempting soft delete of ID 1...")
    success, msg = captured_data_service.delete_records([1], soft_delete=True)
    logger.info(f"Service result: success={success}, msg='{msg}'")

    # 3. Check status again
    session = SessionLocal()
    r = session.query(CapturedData).filter_by(id=1).first()
    logger.info(f"After delete: ID={r.id}, is_deleted={r.is_deleted}")
    
    # 4. Check if get_captured_data filters it out
    result = captured_data_service.get_captured_data()
    ids = [d.id for d in result['data']]
    logger.info(f"IDs in get_captured_data: {ids}")
    if 1 in ids:
        logger.error("ID 1 still appears in get_captured_data results!")
    else:
        logger.info("ID 1 successfully filtered out.")
        
    # Restore it for future tests if needed (optional)
    # session.query(CapturedData).filter_by(id=1).update({CapturedData.is_deleted: False})
    # session.commit()
    session.close()

if __name__ == "__main__":
    test_deletion()
