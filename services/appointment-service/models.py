"""
Database Models for Appointment Service.

This module defines SQLAlchemy ORM models for appointments (FHIR R4 compatible).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class Appointment(Base):
    """
    Appointment model (FHIR Appointment compatible).

    Represents scheduled healthcare appointments with FHIR R4 compatibility.
    """

    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String(50), default="Appointment", nullable=False)
    identifier = Column(JSONB)
    status = Column(String(50), nullable=False, index=True)
    service_category = Column(String(100))
    service_type = Column(String(100))
    specialty = Column(String(100), index=True)
    appointment_type = Column(String(100))
    reason_code = Column(JSONB)
    reason_reference = Column(String(100))
    priority = Column(Integer)
    description = Column(Text)
    start = Column(DateTime, nullable=False, index=True)
    end = Column(DateTime, nullable=False, index=True)
    minute_duration = Column(Integer)
    slot = Column(JSONB)
    created = Column(DateTime)
    comment = Column(Text)
    requested_period = Column(JSONB)
    participant = Column(JSONB, nullable=False)
    location = Column(String(255))
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of Appointment."""
        return f"<Appointment(id={self.id}, status={self.status}, start={self.start})>"
