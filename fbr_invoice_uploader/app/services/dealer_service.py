from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Customer, CustomerType
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class DealerService:
    def __init__(self):
        pass

    def get_db(self):
        return SessionLocal()

    def create_dealer(self, cnic: str, name: str, father_name: str, business_name: str, phone: str, address: str) -> Customer:
        """Create a new dealer (Customer with type DEALER)."""
        db = self.get_db()
        try:
            dealer = Customer(
                cnic=cnic,
                name=(name or "").upper(),
                father_name=(father_name or "").upper(),
                business_name=(business_name or "").upper(),
                phone=phone,
                address=(address or "").upper(),
                type=CustomerType.DEALER.value
            )
            db.add(dealer)
            db.commit()
            db.refresh(dealer)
            return dealer
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating dealer: {e}")
            raise e
        finally:
            db.close()

    def get_dealer_by_business_name(self, business_name: str) -> Optional[Customer]:
        """Get a dealer by business name (case insensitive)."""
        db = self.get_db()
        try:
            return db.query(Customer).filter(
                Customer.business_name.ilike(business_name),
                Customer.type == CustomerType.DEALER.value
            ).first()
        finally:
            db.close()

    def get_dealer_by_id(self, dealer_id: int) -> Optional[Customer]:
        """Get a dealer by ID."""
        db = self.get_db()
        try:
            return db.query(Customer).filter(
                Customer.id == dealer_id,
                Customer.type == CustomerType.DEALER.value
            ).first()
        finally:
            db.close()

    def get_all_dealers(self) -> List[Customer]:
        """Get all dealers."""
        db = self.get_db()
        try:
            return db.query(Customer).filter(Customer.type == CustomerType.DEALER.value).all()
        finally:
            db.close()

    def update_dealer(self, dealer_id: int, cnic: str, name: str, father_name: str, business_name: str, phone: str, address: str) -> Optional[Customer]:
        """Update an existing dealer."""
        db = self.get_db()
        try:
            dealer = db.query(Customer).filter(
                Customer.id == dealer_id,
                Customer.type == CustomerType.DEALER.value
            ).first()
            if dealer:
                dealer.cnic = cnic
                dealer.name = (name or "").upper()
                dealer.father_name = (father_name or "").upper()
                dealer.business_name = (business_name or "").upper()
                dealer.phone = phone
                dealer.address = (address or "").upper()
                db.commit()
                db.refresh(dealer)
                return dealer
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating dealer: {e}")
            raise e
        finally:
            db.close()

    def delete_dealer(self, dealer_id: int):
        """Delete a dealer by ID."""
        db = self.get_db()
        try:
            dealer = db.query(Customer).filter(
                Customer.id == dealer_id,
                Customer.type == CustomerType.DEALER.value
            ).first()
            if dealer:
                db.delete(dealer)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting dealer: {e}")
            raise e
        finally:
            db.close()

    def close(self):
        pass # No longer needed as we close per request

dealer_service = DealerService()
