"""
Pydantic Schemas for Appointment Service.

FHIR R4 Compatible Appointment Resource Models.
Reference: https://www.hl7.org/fhir/appointment.html
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AppointmentStatusEnum(str, Enum):
    """FHIR Appointment Status codes."""

    PROPOSED = "proposed"
    PENDING = "pending"
    BOOKED = "booked"
    ARRIVED = "arrived"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    NO_SHOW = "noshow"
    ENTERED_IN_ERROR = "entered-in-error"
    CHECKED_IN = "checked-in"
    WAITLIST = "waitlist"


class ParticipationStatusEnum(str, Enum):
    """FHIR Participation Status codes."""

    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needs-action"


class ParticipantTypeEnum(str, Enum):
    """FHIR Participant Type codes."""

    PATIENT = "patient"
    PRACTITIONER = "practitioner"
    RELATED_PERSON = "related-person"
    DEVICE = "device"
    HEALTH_CARE_SERVICE = "health-care-service"
    LOCATION = "location"


class AppointmentParticipant(BaseModel):
    """FHIR Appointment Participant schema."""

    type: Optional[List[ParticipantTypeEnum]] = Field(
        None, description="Role of participant"
    )
    actor: Optional[str] = Field(
        None, description="Reference to resource - Patient/Practitioner ID"
    )
    required: Optional[str] = Field(
        None, description="required | optional | information-only"
    )
    status: ParticipationStatusEnum = Field(
        ..., description="accepted | declined | tentative | needs-action"
    )
    period_start: Optional[datetime] = Field(
        None, description="Participation period start"
    )
    period_end: Optional[datetime] = Field(None, description="Participation period end")

    class Config:
        json_schema_extra = {
            "example": {
                "type": ["patient"],
                "actor": "pat-12345",
                "required": "required",
                "status": "accepted",
            }
        }


class AppointmentCreate(BaseModel):
    """Appointment Creation Request schema."""

    identifier: Optional[List[Dict[str, Any]]] = Field(
        None, description="External Ids for appointment"
    )
    status: AppointmentStatusEnum = Field(default=AppointmentStatusEnum.PROPOSED)
    service_category: Optional[str] = Field(
        None, description="General categorization of appointment"
    )
    service_type: Optional[str] = Field(None, description="Type of service/specialty")
    specialty: Optional[str] = Field(
        None, description="The specialty of a practitioner"
    )
    appointment_type: Optional[str] = Field(
        None, description="The style of appointment or patient preference"
    )
    reason_code: Optional[List[str]] = Field(
        None, description="Why appointment needed (ICD-10 codes)"
    )
    reason_reference: Optional[str] = Field(
        None, description="Reference to resource (Condition ID)"
    )
    priority: Optional[int] = Field(
        None, ge=0, le=10, description="Priority of appointment (0-10)"
    )
    description: Optional[str] = Field(
        None, description="Shown on a subject line in a meeting request"
    )
    start: datetime = Field(..., description="When appointment is to take place")
    end: datetime = Field(..., description="When appointment is to conclude")
    minute_duration: Optional[int] = Field(
        None, description="How long appointment is to take (minutes)"
    )
    slot: Optional[List[str]] = Field(
        None, description="The slots that this appointment is allocated"
    )
    created: Optional[datetime] = Field(None, description="Appointment creation date")
    comment: Optional[str] = Field(
        None, description="Additional comments about appointment"
    )
    requested_period: Optional[List[Dict[str, datetime]]] = Field(
        None, description="Potential date/time requested by requestor"
    )
    patient_id: str = Field(..., description="Patient for this appointment")
    practitioner_name: Optional[str] = Field(None, description="Practitioner name")
    practitioner_id: Optional[str] = Field(None, description="Practitioner ID")
    location: Optional[str] = Field(
        None, description="The location appointments are to be held"
    )

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate end time is after start time."""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("End time must be after start time")
        return v

    @field_validator("start")
    @classmethod
    def start_in_future(cls, v: datetime) -> datetime:
        """Validate start time is in future."""
        now = datetime.now(timezone.utc)
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware < now:
            raise ValueError("Appointment start time must be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "booked",
                "start": "2025-12-15T09:00:00Z",
                "end": "2025-12-15T10:00:00Z",
                "patient_id": "pat-12345",
                "practitioner_name": "Dr. Jane Doe",
                "description": "Annual checkup",
            }
        }


class AppointmentUpdate(BaseModel):
    """Appointment Update Request schema."""

    status: Optional[AppointmentStatusEnum] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    comment: Optional[str] = None
    specialty: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "fulfilled",
                "comment": "Patient arrived on time",
            }
        }


class AppointmentResponse(BaseModel):
    """Appointment Response schema."""

    id: str = Field(..., description="Logical id of this artifact")
    resource_type: str = Field(default="Appointment", description="FHIR resource type")
    identifier: Optional[List[Dict[str, Any]]] = None
    status: AppointmentStatusEnum
    service_type: Optional[str] = None
    specialty: Optional[str] = None
    appointment_type: Optional[str] = None
    reason_code: Optional[List[str]] = None
    reason_reference: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    start: datetime
    end: datetime
    minute_duration: Optional[int] = None
    comment: Optional[str] = None
    participant: List[AppointmentParticipant]
    location: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, "hex"):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "resource_type": "Appointment",
                "id": "apt-67890",
                "status": "booked",
                "start": "2025-12-15T09:00:00Z",
                "end": "2025-12-15T10:00:00Z",
                "participant": [
                    {
                        "type": ["patient"],
                        "actor": "pat-12345",
                        "status": "accepted",
                    }
                ],
                "created_at": "2025-11-29T10:00:00Z",
                "updated_at": "2025-11-29T10:00:00Z",
            }
        }


class AppointmentList(BaseModel):
    """List of Appointments schema."""

    total: int
    count: int
    skip: int
    limit: int
    items: List[AppointmentResponse]


class HealthCheck(BaseModel):
    """Health check response schema."""

    status: str
    service: str
    version: str
    database: Optional[str] = None
