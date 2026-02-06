from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Customer, CustomerType
from typing import List, Optional

class CustomerService:
    def __init__(self):
        self.db: Session = SessionLocal()

    def check_duplicate_cnic(self, cnic: str, exclude_id: int = None) -> bool:
        if not cnic:
            return False
        query = self.db.query(Customer).filter(Customer.cnic == cnic)
        if exclude_id:
            query = query.filter(Customer.id != exclude_id)
        return query.first() is not None

    def create_customer(self, cnic: str, name: str, father_name: str, phone: str, address: str, ntn: str = None, business_name: str = None, customer_type: str = CustomerType.INDIVIDUAL) -> Customer:
        """Create a new customer."""
        if self.check_duplicate_cnic(cnic):
            raise ValueError(f"CNIC '{cnic}' already exists.")

        try:
            customer = Customer(
                cnic=cnic,
                name=(name or "").upper(),
                father_name=(father_name or "").upper(),
                business_name=(business_name or "").upper() if business_name else None,
                phone=phone,
                address=(address or "").upper(),
                ntn=ntn,
                type=customer_type
            )
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except Exception as e:
            self.db.rollback()
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                if "cnic" in str(e).lower():
                    raise ValueError(f"CNIC '{cnic}' already exists.")
            raise e

    def get_customer_by_cnic(self, cnic: str) -> Optional[Customer]:
        """Get a customer by CNIC."""
        return self.db.query(Customer).filter(Customer.cnic == cnic).first()

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_all_customers(self) -> List[Customer]:
        """Get all customers."""
        return self.db.query(Customer).order_by(Customer.id.desc()).all()

    def search_customers(self, query: str) -> List[Customer]:
        """Search customers by name, cnic, or phone."""
        search = f"%{query}%"
        return self.db.query(Customer).filter(
            (Customer.name.ilike(search)) |
            (Customer.cnic.ilike(search)) |
            (Customer.phone.ilike(search)) |
            (Customer.business_name.ilike(search))
        ).order_by(Customer.id.desc()).limit(50).all()

    def update_customer(self, customer_id: int, cnic: str, name: str, father_name: str, phone: str, address: str, ntn: str = None, business_name: str = None, customer_type: str = CustomerType.INDIVIDUAL) -> Optional[Customer]:
        """Update an existing customer."""
        if self.check_duplicate_cnic(cnic, exclude_id=customer_id):
            raise ValueError(f"CNIC '{cnic}' already exists.")

        customer = self.get_customer_by_id(customer_id)
        if customer:
            try:
                customer.cnic = cnic
                customer.name = (name or "").upper()
                customer.father_name = (father_name or "").upper()
                customer.business_name = (business_name or "").upper() if business_name else None
                customer.phone = phone
                customer.address = (address or "").upper()
                customer.ntn = ntn
                customer.type = customer_type
                self.db.commit()
                self.db.refresh(customer)
                return customer
            except Exception as e:
                self.db.rollback()
                if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                    if "cnic" in str(e).lower():
                        raise ValueError(f"CNIC '{cnic}' already exists.")
                raise e
        return None

    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer by ID."""
        customer = self.get_customer_by_id(customer_id)
        if customer:
            try:
                self.db.delete(customer)
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
                return False
        return False

    def close(self):
        self.db.close()

customer_service = CustomerService()
