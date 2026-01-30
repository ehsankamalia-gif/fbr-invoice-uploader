from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

# Independent Base for Excise Module
ExciseBase = declarative_base()

class ExciseOwner(ExciseBase):
    __tablename__ = "excise_owners"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    father_name = Column(String(100))
    cnic = Column(String(20), unique=True, index=True)
    address = Column(String(255))
    city = Column(String(50))
    
    registrations = relationship("ExciseRegistration", back_populates="owner")

class ExciseVehicle(ExciseBase):
    __tablename__ = "excise_vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String(50), unique=True, index=True, nullable=False)
    engine_number = Column(String(50), nullable=False)
    make = Column(String(50))
    model = Column(String(50))
    year = Column(Integer)
    color = Column(String(30))
    horsepower = Column(String(20))
    seating_capacity = Column(Integer)
    
    registrations = relationship("ExciseRegistration", back_populates="vehicle")

class ExciseRegistration(ExciseBase):
    __tablename__ = "excise_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String(20), unique=True, index=True, nullable=False)
    registration_date = Column(Date)
    token_tax_paid_upto = Column(Date)
    
    owner_id = Column(Integer, ForeignKey("excise_owners.id"))
    vehicle_id = Column(Integer, ForeignKey("excise_vehicles.id"))
    
    owner = relationship("ExciseOwner", back_populates="registrations")
    vehicle = relationship("ExciseVehicle", back_populates="registrations")
    payments = relationship("ExcisePayment", back_populates="registration")

class ExcisePayment(ExciseBase):
    __tablename__ = "excise_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, default=datetime.now)
    challan_number = Column(String(50))
    payment_type = Column(String(50)) # e.g., "Token Tax", "Registration Fee"
    
    registration_id = Column(Integer, ForeignKey("excise_registrations.id"))
    
    registration = relationship("ExciseRegistration", back_populates="payments")
