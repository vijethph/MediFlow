"""
Database Models for Prescription Service.

This module defines Pydantic models for MongoDB documents.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler):
        return {"type": "string"}


class PrescriptionStatus(str, Enum):
    """Prescription status codes."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered-in-error"
    STOPPED = "stopped"


class MedicationFrequency(str, Enum):
    """Medication frequency codes."""

    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    AS_NEEDED = "as_needed"
    EVERY_MORNING = "every_morning"
    EVERY_EVENING = "every_evening"


class LabResultStatus(str, Enum):
    """Lab result status codes."""

    REGISTERED = "registered"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"


class MedicalRecordType(str, Enum):
    """Medical record type codes."""

    CONSULTATION = "consultation"
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    IMAGING = "imaging"
    DISCHARGE_SUMMARY = "discharge_summary"
    PROGRESS_NOTE = "progress_note"


class Medication(BaseModel):
    """Medication item in prescription."""

    medication_name: str = Field(..., description="Name of medication")
    dosage: str = Field(..., description="Dosage (e.g., '500mg')")
    frequency: MedicationFrequency = Field(..., description="Frequency of administration")
    duration_days: int = Field(..., description="Duration in days", ge=1)
    instructions: Optional[str] = Field(None, description="Special instructions")
    quantity: Optional[int] = Field(None, description="Total quantity prescribed")

    class Config:
        use_enum_values = True


class Prescription(BaseModel):
    """Prescription document model."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    prescription_id: str = Field(..., description="Unique prescription identifier")
    patient_id: str = Field(..., description="Patient identifier")
    doctor_name: str = Field(..., description="Prescribing doctor name")
    doctor_id: Optional[str] = Field(None, description="Doctor identifier")
    appointment_id: Optional[str] = Field(None, description="Related appointment ID")
    
    medications: List[Medication] = Field(..., description="List of prescribed medications")
    diagnosis: str = Field(..., description="Diagnosis or reason for prescription")
    notes: Optional[str] = Field(None, description="Additional clinical notes")
    
    status: PrescriptionStatus = Field(
        default=PrescriptionStatus.ACTIVE, description="Prescription status"
    )
    
    prescribed_date: datetime = Field(
        default_factory=datetime.utcnow, description="Date prescription was written"
    )
    valid_until: Optional[datetime] = Field(None, description="Expiration date")
    
    lab_tests_ordered: Optional[List[str]] = Field(
        None, description="Lab tests ordered with prescription"
    )
    follow_up_required: bool = Field(default=False, description="Follow-up appointment needed")
    follow_up_days: Optional[int] = Field(None, description="Days until follow-up")
    
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "prescription_id": "RX-2025-001",
                "patient_id": "pat-123",
                "doctor_name": "Dr. Sarah Johnson",
                "appointment_id": "apt-456",
                "medications": [
                    {
                        "medication_name": "Amoxicillin",
                        "dosage": "500mg",
                        "frequency": "three_times_daily",
                        "duration_days": 7,
                        "instructions": "Take with food",
                    }
                ],
                "diagnosis": "Acute bacterial sinusitis",
                "status": "active",
            }
        }


class MedicalRecord(BaseModel):
    """Medical record document model."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    record_id: str = Field(..., description="Unique record identifier")
    patient_id: str = Field(..., description="Patient identifier")
    
    record_type: MedicalRecordType = Field(..., description="Type of medical record")
    title: str = Field(..., description="Record title")
    description: str = Field(..., description="Detailed description")
    
    doctor_name: str = Field(..., description="Attending doctor name")
    doctor_id: Optional[str] = Field(None, description="Doctor identifier")
    
    appointment_id: Optional[str] = Field(None, description="Related appointment ID")
    prescription_id: Optional[str] = Field(None, description="Related prescription ID")
    
    vital_signs: Optional[Dict[str, Any]] = Field(
        None, description="Vital signs (BP, temp, pulse, etc.)"
    )
    symptoms: Optional[List[str]] = Field(None, description="Reported symptoms")
    diagnosis_codes: Optional[List[str]] = Field(None, description="ICD-10 diagnosis codes")
    
    attachments: Optional[List[Dict[str, str]]] = Field(
        None, description="Document attachments (file_name, file_url, file_type)"
    )
    
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        use_enum_values = True


class LabTest(BaseModel):
    """Individual lab test within lab results."""

    test_name: str = Field(..., description="Name of the test")
    test_code: Optional[str] = Field(None, description="Lab test code (LOINC)")
    result_value: str = Field(..., description="Test result value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    reference_range: Optional[str] = Field(None, description="Normal reference range")
    abnormal_flag: Optional[str] = Field(None, description="Abnormal indicator (H, L, N)")
    notes: Optional[str] = Field(None, description="Test-specific notes")


class LabResult(BaseModel):
    """Lab result document model."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    result_id: str = Field(..., description="Unique result identifier")
    patient_id: str = Field(..., description="Patient identifier")
    
    test_panel_name: str = Field(..., description="Name of test panel")
    test_category: str = Field(..., description="Category (Hematology, Chemistry, etc.)")
    
    tests: List[LabTest] = Field(..., description="Individual test results")
    
    ordering_doctor: str = Field(..., description="Doctor who ordered tests")
    performing_lab: str = Field(..., description="Laboratory that performed tests")
    
    test_date: datetime = Field(..., description="Date tests were performed")
    result_date: datetime = Field(..., description="Date results were released")
    
    status: LabResultStatus = Field(
        default=LabResultStatus.PRELIMINARY, description="Result status"
    )
    
    interpretation: Optional[str] = Field(None, description="Overall interpretation")
    critical_results: bool = Field(default=False, description="Contains critical values")
    
    appointment_id: Optional[str] = Field(None, description="Related appointment ID")
    prescription_id: Optional[str] = Field(None, description="Related prescription ID")
    
    attachments: Optional[List[Dict[str, str]]] = Field(
        None, description="Report attachments (PDF, images)"
    )
    
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        use_enum_values = True