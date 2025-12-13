"""
Pydantic Schemas for Patient Service.

This module defines FHIR R4 compatible request/response schemas for patients.
Reference: https://www.hl7.org/fhir/patient.html
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class GenderEnum(str, Enum):
    """FHIR Gender codes."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ContactPointSystemEnum(str, Enum):
    """FHIR Contact Point System."""

    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    SMS = "sms"
    URL = "url"


class HumanName(BaseModel):
    """
    FHIR Human Name Resource.

    Reference: https://www.hl7.org/fhir/datatypes.html#HumanName
    """

    use: Optional[str] = Field(
        None, description="usual | official | temp | nickname | old | maiden"
    )
    text: Optional[str] = Field(
        None, description="Text representation of the full name"
    )
    family: Optional[str] = Field(None, description="Family name (Surname)")
    given: Optional[List[str]] = Field(None, description="Given names")
    prefix: Optional[List[str]] = Field(None, description="Parts before the name")
    suffix: Optional[List[str]] = Field(None, description="Parts after the name")

    class Config:
        json_schema_extra = {
            "example": {
                "use": "official",
                "family": "Smith",
                "given": ["John", "Michael"],
            }
        }


class ContactPoint(BaseModel):
    """
    FHIR Contact Point Resource.

    Reference: https://www.hl7.org/fhir/datatypes.html#ContactPoint
    """

    system: ContactPointSystemEnum
    value: str = Field(..., description="The actual contact point details")
    use: Optional[str] = Field(None, description="home | work | temp | old | mobile")
    rank: Optional[int] = Field(None, description="Specify preferred order")

    class Config:
        json_schema_extra = {
            "example": {
                "system": "email",
                "value": "john.smith@example.com",
                "use": "work",
            }
        }


class Address(BaseModel):
    """
    FHIR Address Resource.

    Reference: https://www.hl7.org/fhir/datatypes.html#Address
    """

    use: Optional[str] = Field(None, description="home | work | temp | old")
    type: Optional[str] = Field(None, description="postal | physical | both")
    text: Optional[str] = Field(None, description="Text representation of address")
    line: Optional[List[str]] = Field(None, description="Street address lines")
    city: Optional[str] = Field(None, description="Name of city/town")
    district: Optional[str] = Field(None, description="District name (county)")
    state: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal code for area")
    country: Optional[str] = Field(None, description="Country (ISO 3166 3-letter code)")
    period_start: Optional[datetime] = Field(
        None, description="Time period start (if known)"
    )
    period_end: Optional[datetime] = Field(
        None, description="Time period end (if known)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "use": "home",
                "type": "physical",
                "line": ["123 Main Street", "Apt 4"],
                "city": "Boston",
                "state": "MA",
                "postal_code": "02101",
                "country": "USA",
            }
        }


class Identifier(BaseModel):
    """
    FHIR Identifier Resource.

    Reference: https://www.hl7.org/fhir/datatypes.html#Identifier
    """

    use: Optional[str] = Field(
        None, description="usual | official | temp | secondary | old"
    )
    type: Optional[str] = Field(None, description="Description of identifier")
    system: Optional[str] = Field(
        None, description="The namespace for the identifier value"
    )
    value: str = Field(..., description="The value that is unique")

    class Config:
        json_schema_extra = {
            "example": {
                "system": "http://hospital.org/patient-id",
                "value": "PAT-12345",
            }
        }


class PatientCreate(BaseModel):
    """Patient Creation Request (FHIR-Compatible)."""

    name: List[HumanName] = Field(..., description="A name associated with the patient")
    telecom: Optional[List[ContactPoint]] = Field(
        None, description="A contact detail for the patient"
    )
    gender: Optional[GenderEnum] = Field(
        None, description="male | female | other | unknown"
    )
    birth_date: Optional[date] = Field(
        None, description="The date of birth for the patient"
    )
    address: Optional[List[Address]] = Field(
        None, description="An address for the patient"
    )
    marital_status: Optional[str] = Field(None, description="Marital (civil) status")
    multiple_births_integer: Optional[int] = Field(
        None, description="Whether patient is part of multiple birth"
    )
    contact: Optional[List[Dict[str, Any]]] = Field(
        None, description="A contact party for the patient"
    )
    communication: Optional[List[Dict[str, Any]]] = Field(
        None, description="Language which may be used to communicate"
    )
    general_practitioner: Optional[List[Dict[str, Any]]] = Field(
        None, description="Patient's nominated primary care provider"
    )
    managing_organization: Optional[str] = Field(
        None, description="Organization that is the custodian of patient record"
    )

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v):
        """Validate birth date."""
        if v and v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
                "telecom": [{"system": "email", "value": "john.smith@example.com"}],
                "gender": "male",
                "birth_date": "1990-01-15",
            }
        }


class PatientUpdate(BaseModel):
    """Patient Update Request (FHIR-Compatible)."""

    name: Optional[List[HumanName]] = None
    telecom: Optional[List[ContactPoint]] = None
    gender: Optional[GenderEnum] = None
    birth_date: Optional[date] = None
    address: Optional[List[Address]] = None
    marital_status: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"telecom": [{"system": "phone", "value": "+1-555-0100"}]}
        }


class PatientResponse(BaseModel):
    """Patient Response Model (FHIR-Compatible)."""

    id: str = Field(..., description="Logical id of this artifact (FHIR Patient ID)")
    resource_type: str = Field(default="Patient", description="FHIR resource type")
    identifier: Optional[List[Identifier]] = Field(
        None, description="An identifier for this patient"
    )
    active: bool = Field(
        default=True, description="Whether this patient's record is in active use"
    )
    name: List[HumanName]
    telecom: Optional[List[ContactPoint]] = None
    gender: Optional[GenderEnum] = None
    birth_date: Optional[date] = None
    address: Optional[List[Address]] = None
    marital_status: Optional[str] = None
    contact: Optional[List[Dict[str, Any]]] = None
    general_practitioner: Optional[List[Dict[str, Any]]] = None
    managing_organization: Optional[str] = None
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the resource"
    )
    created_at: datetime = Field(..., description="Timestamp of creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "resource_type": "Patient",
                "id": "pat-12345",
                "active": True,
                "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
                "gender": "male",
                "birth_date": "1990-01-15",
                "created_at": "2025-11-29T10:00:00Z",
                "updated_at": "2025-11-29T10:00:00Z",
            }
        }


class PatientList(BaseModel):
    """List of Patients."""

    total: int
    count: int
    skip: int
    limit: int
    items: List[PatientResponse]


class Token(BaseModel):
    """JWT Token Response."""

    access_token: str
    token_type: str = "bearer"
    patient_id: str
    email: str


class PatientLogin(BaseModel):
    """Patient Login Request."""

    email: EmailStr
    password: Optional[str] = None


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
