"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date, time
from models import AppointmentStatus, AppointmentPriority


class AppointmentBase(BaseModel):
    """Base appointment schema with common fields."""
    patient_id: str = Field(..., min_length=1, max_length=20, description="Patient ID")
    patient_name: Optional[str] = Field(None, max_length=255, description="Patient name (denormalized)")
    patient_email: Optional[EmailStr] = Field(None, description="Patient email (denormalized)")
    doctor_id: str = Field(..., min_length=1, max_length=50, description="Doctor ID")
    doctor_name: str = Field(..., min_length=1, max_length=255, description="Doctor name")
    doctor_specialization: Optional[str] = Field(None, max_length=100, description="Doctor specialization")
    doctor_email: Optional[EmailStr] = Field(None, description="Doctor email")
    appointment_date: datetime = Field(..., description="Appointment date and time")
    appointment_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', description="Appointment time (HH:MM)")
    duration_minutes: int = Field(30, ge=15, le=240, description="Appointment duration in minutes")
    priority: AppointmentPriority = Field(AppointmentPriority.ROUTINE, description="Appointment priority")
    reason: Optional[str] = Field(None, description="Reason for appointment")
    description: Optional[str] = Field(None, description="Appointment description")
    notes: Optional[str] = Field(None, description="Additional notes")
    location: Optional[str] = Field(None, max_length=255, description="Appointment location")
    room_number: Optional[str] = Field(None, max_length=50, description="Room number")
    
    @validator('appointment_date')
    def validate_appointment_date(cls, v):
        """Validate appointment date is in the future."""
        if v < datetime.now():
            raise ValueError('Appointment date must be in the future')
        return v


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""
    pass


class AppointmentUpdate(BaseModel):
    """Schema for updating appointment (all fields optional)."""
    patient_id: Optional[str] = Field(None, max_length=20)
    patient_name: Optional[str] = Field(None, max_length=255)
    patient_email: Optional[EmailStr] = None
    doctor_id: Optional[str] = Field(None, max_length=50)
    doctor_name: Optional[str] = Field(None, max_length=255)
    doctor_specialization: Optional[str] = Field(None, max_length=100)
    doctor_email: Optional[EmailStr] = None
    appointment_date: Optional[datetime] = None
    appointment_time: Optional[str] = Field(None, pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    duration_minutes: Optional[int] = Field(None, ge=15, le=240)
    status: Optional[AppointmentStatus] = None
    priority: Optional[AppointmentPriority] = None
    reason: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    diagnosis: Optional[str] = None
    follow_up_required: Optional[bool] = None
    location: Optional[str] = Field(None, max_length=255)
    room_number: Optional[str] = Field(None, max_length=50)
    cancellation_reason: Optional[str] = None
    
    @validator('appointment_date')
    def validate_appointment_date(cls, v):
        """Validate appointment date is in the future if provided."""
        if v and v < datetime.now():
            raise ValueError('Appointment date must be in the future')
        return v


class Appointment(AppointmentBase):
    """Schema for appointment response."""
    id: int
    appointment_id: str
    end_time: Optional[datetime]
    status: AppointmentStatus
    diagnosis: Optional[str]
    follow_up_required: bool
    reminder_sent: bool
    notification_sent: bool
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    cancelled_by: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class AppointmentCancel(BaseModel):
    """Schema for cancelling an appointment."""
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")
    cancelled_by: Optional[str] = Field(None, max_length=100, description="User who cancelled")


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling an appointment."""
    new_appointment_date: datetime = Field(..., description="New appointment date and time")
    new_appointment_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', description="New appointment time (HH:MM)")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")
    
    @validator('new_appointment_date')
    def validate_appointment_date(cls, v):
        """Validate appointment date is in the future."""
        if v < datetime.now():
            raise ValueError('Appointment date must be in the future')
        return v


class AppointmentSearch(BaseModel):
    """Schema for appointment search filters."""
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_specialization: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    priority: Optional[AppointmentPriority] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True


class DoctorAvailabilityBase(BaseModel):
    """Base schema for doctor availability."""
    doctor_id: str = Field(..., max_length=50)
    doctor_name: str = Field(..., max_length=255)
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    end_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    is_available: bool = Field(True)
    date_specific: Optional[datetime] = None
    notes: Optional[str] = None


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    """Schema for creating doctor availability."""
    pass


class DoctorAvailability(DoctorAvailabilityBase):
    """Schema for doctor availability response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str
    service: str
    version: str
    database: Optional[str] = None

