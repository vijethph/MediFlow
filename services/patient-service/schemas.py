"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import date, datetime


class PatientBase(BaseModel):
    """Base patient schema with common fields."""
    full_name: str = Field(..., min_length=1, max_length=255, description="Patient's full name")
    email: EmailStr = Field(..., description="Patient's email address")
    phone: Optional[str] = Field(None, max_length=20, description="Patient's phone number")
    date_of_birth: Optional[date] = Field(None, description="Patient's date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, max_length=20, description="Patient's gender")
    address: Optional[str] = Field(None, description="Patient's address")
    blood_group: Optional[str] = Field(None, max_length=10, description="Patient's blood group")
    allergies: Optional[str] = Field(None, description="Known allergies")
    medical_history: Optional[str] = Field(None, description="Medical history")
    current_medications: Optional[str] = Field(None, description="Current medications")
    emergency_contact_name: Optional[str] = Field(None, max_length=255, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, max_length=20, description="Emergency contact phone")
    
    @validator('phone', 'emergency_contact_phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v is None:
            return v
        # Remove common separators
        cleaned = v.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').replace('+', '')
        # Check if it contains only digits
        if not cleaned.isdigit():
            raise ValueError('Phone number must contain only digits and common separators')
        # Check length
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError('Phone number must be between 7 and 15 digits')
        return v
    
    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth."""
        if v is None:
            return v
        from datetime import date
        today = date.today()
        if v >= today:
            raise ValueError('Date of birth must be in the past')
        # Check if date is reasonable (not more than 150 years ago)
        age = (today - v).days / 365.25
        if age > 150:
            raise ValueError('Date of birth is not reasonable')
        return v


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating patient information (all fields optional)."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    blood_group: Optional[str] = Field(None, max_length=10)
    allergies: Optional[str] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    
    @validator('phone', 'emergency_contact_phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v is None:
            return v
        cleaned = v.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').replace('+', '')
        if not cleaned.isdigit():
            raise ValueError('Phone number must contain only digits and common separators')
        # Check length
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError('Phone number must be between 7 and 15 digits')
        return v


class Patient(PatientBase):
    """Schema for patient response."""
    id: int
    patient_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class PatientLogin(BaseModel):
    """Schema for patient login."""
    email: EmailStr
    password: Optional[str] = None  # For future password-based auth


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    patient_id: str
    email: str


class TokenData(BaseModel):
    """Schema for decoded token data."""
    patient_id: Optional[str] = None
    email: Optional[str] = None


class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str
    service: str
    version: str
    database: Optional[str] = None

