"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Index, Boolean
from sqlalchemy.sql import func
from database import Base
import enum
import uuid


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"


class AppointmentPriority(str, enum.Enum):
    """Appointment priority enumeration."""
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"


def generate_appointment_id() -> str:
    """Generate unique appointment ID in format APT-XXXXX."""
    unique_id = str(uuid.uuid4()).replace("-", "").upper()[:8]
    return f"APT-{unique_id}"


class Appointment(Base):
    """Appointment model representing appointments table in database."""
    
    __tablename__ = "appointments"
    
    # Identifiers
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(String(20), unique=True, index=True, nullable=False)
    
    # Patient Information
    patient_id = Column(String(20), nullable=False, index=True)
    patient_name = Column(String(255), nullable=True)  # Denormalized for performance
    patient_email = Column(String(255), nullable=True)  # Denormalized for performance
    
    # Doctor Information
    doctor_id = Column(String(50), nullable=False, index=True)
    doctor_name = Column(String(255), nullable=False, index=True)
    doctor_specialization = Column(String(100), nullable=True, index=True)
    doctor_email = Column(String(255), nullable=True)
    
    # Appointment Details
    appointment_date = Column(DateTime(timezone=True), nullable=False, index=True)
    appointment_time = Column(String(10), nullable=False)  # Format: HH:MM
    duration_minutes = Column(Integer, default=30, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Status and Priority
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING, nullable=False, index=True)
    priority = Column(Enum(AppointmentPriority), default=AppointmentPriority.ROUTINE, nullable=False)
    
    # Appointment Information
    reason = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)  # Added after appointment
    follow_up_required = Column(Boolean, default=False, nullable=False)
    
    # Location
    location = Column(String(255), nullable=True)
    room_number = Column(String(50), nullable=True)
    
    # Reminders and Notifications
    reminder_sent = Column(Boolean, default=False, nullable=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    notification_sent = Column(Boolean, default=False, nullable=False)
    
    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String(100), nullable=True)
    
    # System Fields
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # Indexes for frequently queried fields
    __table_args__ = (
        Index('idx_appointment_date_status', 'appointment_date', 'status'),
        Index('idx_appointment_doctor_date', 'doctor_id', 'appointment_date'),
        Index('idx_patient_date', 'patient_id', 'appointment_date'),
        Index('idx_status_active', 'status', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<Appointment(appointment_id={self.appointment_id}, patient_id={self.patient_id}, doctor_name={self.doctor_name}, appointment_date={self.appointment_date})>"


class DoctorAvailability(Base):
    """Doctor availability model for managing doctor schedules."""
    
    __tablename__ = "doctor_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(String(50), nullable=False, index=True)
    doctor_name = Column(String(255), nullable=False)
    day_of_week = Column(Integer, nullable=False, index=True)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # Format: HH:MM
    end_time = Column(String(10), nullable=False)  # Format: HH:MM
    is_available = Column(Boolean, default=True, nullable=False)
    date_specific = Column(DateTime(timezone=True), nullable=True, index=True)  # For specific date overrides
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_doctor_day', 'doctor_id', 'day_of_week'),
        Index('idx_doctor_date', 'doctor_id', 'date_specific'),
    )
    
    def __repr__(self) -> str:
        return f"<DoctorAvailability(doctor_id={self.doctor_id}, day_of_week={self.day_of_week}, start_time={self.start_time}, end_time={self.end_time})>"

