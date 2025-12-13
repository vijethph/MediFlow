"""
Database Models for Patient Service.

This module defines SQLAlchemy ORM models for FHIR R4 compatible patients.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class Patient(Base):
    """
    Patient model (FHIR Patient compatible).

    Represents a patient record in the healthcare management system.
    Reference: https://www.hl7.org/fhir/patient.html
    """

    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String(50), default="Patient", nullable=False)
    patient_id = Column(String(100), unique=True, nullable=False, index=True)
    identifier = Column(JSONB)
    active = Column(Boolean, default=True, nullable=False, index=True)
    name = Column(JSONB, nullable=False)
    telecom = Column(JSONB)
    gender = Column(String(20))
    birth_date = Column(Date)
    address = Column(JSONB)
    marital_status = Column(String(50))
    multiple_births_integer = Column(String(10))
    contact = Column(JSONB)
    communication = Column(JSONB)
    general_practitioner = Column(JSONB)
    managing_organization = Column(String(255))
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_patient_id_active", "patient_id", "active"),
        Index("idx_patient_birth_date", "birth_date"),
    )

    def __repr__(self) -> str:
        """String representation of Patient."""
        return f"<Patient(id={self.id}, patient_id={self.patient_id}, active={self.active})>"
