from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Customer, CustomerType
from typing import List, Optional

class DealerService:
    def __init__(self):
        self.db: Session = SessionLocal()

    def create_dealer(self, cnic: str, name: str, father_name: str, business_name: str, phone: str, address: str) -> Customer:
        """Create a new dealer (Customer with type DEALER)."""
        try:
            dealer = Customer(
                cnic=cnic,
                name=(name or "").upper(),
                father_name=(father_name or "").upper(),
                business_name=(business_name or "").upper(),
                phone=phone,
                address=(address or "").upper(),
                type=CustomerType.DEALER
            )
            self.db.add(dealer)
            self.db.commit()
            self.db.refresh(dealer)
            return dealer
        except Exception as e:
            self.db.rollback()
            raise e

    def get_dealer_by_business_name(self, business_name: str) -> Optional[Customer]:
        """Get a dealer by business name (case insensitive)."""
        return self.db.query(Customer).filter(
            Customer.business_name.ilike(business_name),
            Customer.type == CustomerType.DEALER
        ).first()

    def get_dealer_by_id(self, dealer_id: int) -> Optional[Customer]:
        """Get a dealer by ID."""
        return self.db.query(Customer).filter(
            Customer.id == dealer_id,
            Customer.type == CustomerType.DEALER
        ).first()

    def get_all_dealers(self) -> List[Customer]:
        """Get all dealers."""
        return self.db.query(Customer).filter(Customer.type == CustomerType.DEALER).all()

    def update_dealer(self, dealer_id: int, cnic: str, name: str, father_name: str, business_name: str, phone: str, address: str) -> Optional[Customer]:
        """Update an existing dealer."""
        dealer = self.db.query(Customer).filter(
            Customer.id == dealer_id,
            Customer.type == CustomerType.DEALER
        ).first()
        if dealer:
            try:
                dealer.cnic = cnic
                dealer.name = (name or "").upper()
                dealer.father_name = (father_name or "").upper()
                dealer.business_name = (business_name or "").upper()
                dealer.phone = phone
                dealer.address = (address or "").upper()
                self.db.commit()
                self.db.refresh(dealer)
                return dealer
            except Exception as e:
                self.db.rollback()
                raise e
        return None

    def delete_dealer(self, dealer_id: int):
        """Delete a dealer by ID."""
        dealer = self.db.query(Customer).filter(
            Customer.id == dealer_id,
            Customer.type == CustomerType.DEALER
        ).first()
        if dealer:
            self.db.delete(dealer)
            self.db.commit()
            return True
        return False

    def close(self):
        self.db.close()

dealer_service = DealerService()
