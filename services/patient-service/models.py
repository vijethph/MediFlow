"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class Patient(Base):
    """Patient model representing patient table in database."""
    
    __tablename__ = "patients"
    
    # Identifiers
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), unique=True, index=True, nullable=False)
    
    # Personal Information
    full_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    
    # Medical Information
    blood_group = Column(String(10), nullable=True)
    allergies = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    
    # Emergency Contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # System Fields
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for frequently queried fields
    __table_args__ = (
        Index('idx_patient_email_active', 'email', 'is_active'),
        Index('idx_patient_id_active', 'patient_id', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<Patient(patient_id={self.patient_id}, email={self.email}, full_name={self.full_name})>"

