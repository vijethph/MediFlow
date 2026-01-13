"""
Pydantic Schemas for Prescription Service.

This module defines request/response schemas for API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from models import (
    LabResultStatus,
    LabTest,
    MedicalRecordType,
    Medication,
    MedicationFrequency,
    PrescriptionStatus,
)


# ============================================
# Prescription Schemas
# ============================================


class MedicationCreate(BaseModel):
    """Schema for creating medication item."""

    medication_name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    frequency: MedicationFrequency
    duration_days: int = Field(..., ge=1, le=365)
    instructions: Optional[str] = Field(None, max_length=500)
    quantity: Optional[int] = Field(None, ge=1)

    class Config:
        use_enum_values = True


class PrescriptionCreate(BaseModel):
    """Schema for creating prescription."""

    patient_id: str = Field(..., min_length=1, description="Patient identifier")
    doctor_name: str = Field(..., min_length=1, max_length=200)
    doctor_id: Optional[str] = None
    appointment_id: Optional[str] = None

    medications: List[MedicationCreate] = Field(..., min_length=1)
    diagnosis: str = Field(..., min_length=1, max_length=1000)
    notes: Optional[str] = Field(None, max_length=2000)

    lab_tests_ordered: Optional[List[str]] = None
    follow_up_required: bool = False
    follow_up_days: Optional[int] = Field(None, ge=1, le=365)

    class Config:
        json_schema_extra = {
            "example": {
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
                        "quantity": 21,
                    }
                ],
                "diagnosis": "Acute bacterial sinusitis",
                "notes": "Patient allergic to penicillin - using alternative",
                "follow_up_required": True,
                "follow_up_days": 14,
            }
        }


class PrescriptionUpdate(BaseModel):
    """Schema for updating prescription."""

    status: Optional[PrescriptionStatus] = None
    notes: Optional[str] = Field(None, max_length=2000)

    class Config:
        use_enum_values = True


class PrescriptionResponse(BaseModel):
    """Schema for prescription response."""

    id: str = Field(..., alias="_id")
    prescription_id: str
    patient_id: str
    doctor_name: str
    doctor_id: Optional[str]
    appointment_id: Optional[str]

    medications: List[Medication]
    diagnosis: str
    notes: Optional[str]

    status: PrescriptionStatus
    prescribed_date: datetime
    valid_until: Optional[datetime]

    lab_tests_ordered: Optional[List[str]]
    follow_up_required: bool
    follow_up_days: Optional[int]

    meta: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class PrescriptionListResponse(BaseModel):
    """Schema for list of prescriptions."""

    total: int
    prescriptions: List[PrescriptionResponse]


# ============================================
# Medical Record Schemas
# ============================================


class VitalSigns(BaseModel):
    """Schema for vital signs."""

    blood_pressure_systolic: Optional[int] = Field(None, ge=50, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=30, le=200)
    heart_rate: Optional[int] = Field(None, ge=30, le=250)
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    oxygen_saturation: Optional[int] = Field(None, ge=70, le=100)
    weight_kg: Optional[float] = Field(None, ge=0.5, le=500.0)
    height_cm: Optional[float] = Field(None, ge=30.0, le=300.0)


class MedicalRecordCreate(BaseModel):
    """Schema for creating medical record."""

    patient_id: str = Field(..., min_length=1)
    record_type: MedicalRecordType
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)

    doctor_name: str = Field(..., min_length=1, max_length=200)
    doctor_id: Optional[str] = None
    appointment_id: Optional[str] = None
    prescription_id: Optional[str] = None

    vital_signs: Optional[VitalSigns] = None
    symptoms: Optional[List[str]] = None
    diagnosis_codes: Optional[List[str]] = None

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "patient_id": "pat-123",
                "record_type": "consultation",
                "title": "Annual Physical Examination",
                "description": "Patient presents for routine annual physical...",
                "doctor_name": "Dr. Sarah Johnson",
                "vital_signs": {
                    "blood_pressure_systolic": 120,
                    "blood_pressure_diastolic": 80,
                    "heart_rate": 72,
                    "temperature": 36.8,
                },
                "symptoms": ["No acute complaints"],
            }
        }


class MedicalRecordUpdate(BaseModel):
    """Schema for updating medical record."""

    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    vital_signs: Optional[VitalSigns] = None


class MedicalRecordResponse(BaseModel):
    """Schema for medical record response."""

    id: str = Field(..., alias="_id")
    record_id: str
    patient_id: str
    record_type: MedicalRecordType
    title: str
    description: str

    doctor_name: str
    doctor_id: Optional[str]
    appointment_id: Optional[str]
    prescription_id: Optional[str]

    vital_signs: Optional[Dict[str, Any]]
    symptoms: Optional[List[str]]
    diagnosis_codes: Optional[List[str]]
    attachments: Optional[List[Dict[str, str]]]

    meta: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
        use_enum_values = True


class MedicalRecordListResponse(BaseModel):
    """Schema for list of medical records."""

    total: int
    records: List[MedicalRecordResponse]


# ============================================
# Lab Result Schemas
# ============================================


class LabTestCreate(BaseModel):
    """Schema for creating lab test."""

    test_name: str = Field(..., min_length=1, max_length=200)
    test_code: Optional[str] = Field(None, max_length=50)
    result_value: str = Field(..., min_length=1, max_length=200)
    unit: Optional[str] = Field(None, max_length=50)
    reference_range: Optional[str] = Field(None, max_length=200)
    abnormal_flag: Optional[str] = Field(None, pattern="^[HLN]$")
    notes: Optional[str] = Field(None, max_length=1000)


class LabResultCreate(BaseModel):
    """Schema for creating lab result."""

    patient_id: str = Field(..., min_length=1)
    test_panel_name: str = Field(..., min_length=1, max_length=200)
    test_category: str = Field(..., min_length=1, max_length=100)

    tests: List[LabTestCreate] = Field(..., min_length=1)

    ordering_doctor: str = Field(..., min_length=1, max_length=200)
    performing_lab: str = Field(..., min_length=1, max_length=200)

    test_date: datetime
    result_date: datetime

    interpretation: Optional[str] = Field(None, max_length=2000)
    critical_results: bool = False

    appointment_id: Optional[str] = None
    prescription_id: Optional[str] = None

    @field_validator("result_date")
    @classmethod
    def validate_result_date(cls, v, info):
        """Ensure result date is not before test date."""
        if "test_date" in info.data and v < info.data["test_date"]:
            raise ValueError("Result date cannot be before test date")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "pat-123",
                "test_panel_name": "Complete Blood Count (CBC)",
                "test_category": "Hematology",
                "tests": [
                    {
                        "test_name": "White Blood Cell Count",
                        "test_code": "6690-2",
                        "result_value": "7.5",
                        "unit": "x10^9/L",
                        "reference_range": "4.0-11.0",
                        "abnormal_flag": "N",
                    }
                ],
                "ordering_doctor": "Dr. Sarah Johnson",
                "performing_lab": "City General Hospital Lab",
                "test_date": "2025-12-01T09:00:00Z",
                "result_date": "2025-12-01T15:00:00Z",
            }
        }


class LabResultUpdate(BaseModel):
    """Schema for updating lab result."""

    status: Optional[LabResultStatus] = None
    interpretation: Optional[str] = Field(None, max_length=2000)

    class Config:
        use_enum_values = True


class LabResultResponse(BaseModel):
    """Schema for lab result response."""

    id: str = Field(..., alias="_id")
    result_id: str
    patient_id: str
    test_panel_name: str
    test_category: str

    tests: List[LabTest]

    ordering_doctor: str
    performing_lab: str

    test_date: datetime
    result_date: datetime
    status: LabResultStatus

    interpretation: Optional[str]
    critical_results: bool

    appointment_id: Optional[str]
    prescription_id: Optional[str]
    attachments: Optional[List[Dict[str, str]]]

    meta: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
        use_enum_values = True


class LabResultListResponse(BaseModel):
    """Schema for list of lab results."""

    total: int
    results: List[LabResultResponse]


# ============================================
# Health Check Schema
# ============================================


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    service: str
    status: str
    database: str
    rabbitmq: Optional[str]
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "service": "prescription-service",
                "status": "healthy",
                "database": "connected",
                "rabbitmq": "connected",
                "timestamp": "2025-12-04T10:00:00Z",
            }
        }
