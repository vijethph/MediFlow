"""
Business Logic Layer for Prescription Service.

This module contains all business logic for prescriptions, medical records, and lab results.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from pymongo.database import Database

import models
import schemas
from common.exceptions import (
    DuplicateResourceError,
    PatientNotFoundError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from common.logging import get_logger
from common.messaging import publish_event_sync
from common.utils import retry_on_api_error
from config import get_settings

settings = get_settings()
logger = get_logger(__name__)


# ============================================
# External Service Integration
# ============================================


@retry_on_api_error(
    max_attempts=3, exceptions=(httpx.RequestError, httpx.HTTPStatusError)
)
async def verify_patient_exists(patient_id: str, jwt_token: str) -> bool:
    """
    Verify patient exists in Patient Service.

    :param patient_id: Patient identifier
    :param jwt_token: JWT authentication token
    :return: True if patient exists
    :raises PatientNotFoundError: If patient not found
    :raises ServiceUnavailableError: If Patient Service unavailable
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.patient_service_url}/api/v1/patients/{patient_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 404:
                raise PatientNotFoundError(patient_id)
            elif response.status_code != 200:
                raise ServiceUnavailableError("Patient Service")

            logger.info("patient_verified", patient_id=patient_id)
            return True
    except httpx.RequestError as e:
        logger.error("patient_service_unavailable", error=str(e))
        raise ServiceUnavailableError("Patient Service") from e


@retry_on_api_error(
    max_attempts=3, exceptions=(httpx.RequestError, httpx.HTTPStatusError)
)
async def get_appointment_details(
    appointment_id: str, jwt_token: str
) -> Optional[Dict[str, Any]]:
    """
    Get appointment details from Appointment Service.

    :param appointment_id: Appointment identifier
    :param jwt_token: JWT authentication token
    :return: Appointment data or None
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.appointment_service_url}/api/v1/appointments/{appointment_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info("appointment_retrieved", appointment_id=appointment_id)
                return response.json()
            else:
                logger.warning("appointment_not_found", appointment_id=appointment_id)
                return None
    except httpx.RequestError as e:
        logger.error("appointment_service_unavailable", error=str(e))
        return None


# ============================================
# Prescription Service Functions
# ============================================


def generate_prescription_id() -> str:
    """Generate unique prescription ID."""
    return f"RX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def create_prescription(
    db: Database, prescription_data: schemas.PrescriptionCreate
) -> models.Prescription:
    """
    Create new prescription.

    :param db: MongoDB database
    :param prescription_data: Prescription creation data
    :return: Created prescription
    """
    logger.info("creating_prescription", patient_id=prescription_data.patient_id)

    # Generate prescription ID
    prescription_id = generate_prescription_id()

    # Calculate valid until date (30 days by default)
    valid_until = datetime.now(timezone.utc) + timedelta(days=30)

    # Create prescription document
    prescription_dict = {
        "prescription_id": prescription_id,
        "patient_id": prescription_data.patient_id,
        "doctor_name": prescription_data.doctor_name,
        "doctor_id": prescription_data.doctor_id,
        "appointment_id": prescription_data.appointment_id,
        "medications": [med.model_dump() for med in prescription_data.medications],
        "diagnosis": prescription_data.diagnosis,
        "notes": prescription_data.notes,
        "status": models.PrescriptionStatus.ACTIVE.value,
        "prescription_date": datetime.now(timezone.utc),
        "prescribed_date": datetime.now(timezone.utc),
        "valid_until": valid_until,
        "lab_tests_ordered": prescription_data.lab_tests_ordered,
        "follow_up_required": prescription_data.follow_up_required,
        "follow_up_days": prescription_data.follow_up_days,
        "meta": {"created_by": "prescription-service"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    # Insert into MongoDB
    result = db.prescriptions.insert_one(prescription_dict)
    prescription_dict["_id"] = result.inserted_id

    logger.info("prescription_created", prescription_id=prescription_id)

    # Publish event
    publish_event_sync(
        "prescription.created",
        {
            "prescription_id": prescription_id,
            "patient_id": prescription_data.patient_id,
            "doctor_name": prescription_data.doctor_name,
            "medication_count": len(prescription_data.medications),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return models.Prescription(**prescription_dict)


def get_prescription_by_id(db: Database, prescription_id: str) -> models.Prescription:
    """
    Get prescription by ID.

    :param db: MongoDB database
    :param prescription_id: Prescription identifier
    :return: Prescription object
    :raises ResourceNotFoundError: If prescription not found
    """
    prescription = db.prescriptions.find_one({"prescription_id": prescription_id})

    if not prescription:
        raise ResourceNotFoundError("Prescription", prescription_id)

    return models.Prescription(**prescription)


def get_prescriptions_by_patient(
    db: Database, patient_id: str, skip: int = 0, limit: int = 100
) -> List[models.Prescription]:
    """
    Get all prescriptions for a patient.

    :param db: MongoDB database
    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: List of prescriptions
    """
    prescriptions = (
        db.prescriptions.find({"patient_id": patient_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    return [models.Prescription(**p) for p in prescriptions]


def update_prescription(
    db: Database, prescription_id: str, prescription_data: schemas.PrescriptionUpdate
) -> models.Prescription:
    """
    Update prescription.

    :param db: MongoDB database
    :param prescription_id: Prescription identifier
    :param prescription_data: Prescription update data
    :return: Updated prescription
    """
    prescription = get_prescription_by_id(db, prescription_id)

    update_dict = {"updated_at": datetime.now(timezone.utc)}

    if prescription_data.status:
        update_dict["status"] = prescription_data.status.value

    if prescription_data.notes is not None:
        update_dict["notes"] = prescription_data.notes

    db.prescriptions.update_one(
        {"prescription_id": prescription_id}, {"$set": update_dict}
    )

    logger.info("prescription_updated", prescription_id=prescription_id)

    # Publish event if status changed
    if prescription_data.status:
        publish_event_sync(
            "prescription.updated",
            {
                "prescription_id": prescription_id,
                "patient_id": prescription.patient_id,
                "new_status": prescription_data.status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return get_prescription_by_id(db, prescription_id)


# ============================================
# Medical Record Service Functions
# ============================================


def generate_record_id() -> str:
    """Generate unique medical record ID."""
    return f"REC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def create_medical_record(
    db: Database, record_data: schemas.MedicalRecordCreate
) -> models.MedicalRecord:
    """
    Create new medical record.

    :param db: MongoDB database
    :param record_data: Medical record creation data
    :return: Created medical record
    """
    logger.info("creating_medical_record", patient_id=record_data.patient_id)

    record_id = generate_record_id()

    record_dict = {
        "record_id": record_id,
        "patient_id": record_data.patient_id,
        "record_type": record_data.record_type,
        "record_date": datetime.now(timezone.utc),
        "title": record_data.title,
        "description": record_data.description,
        "doctor_name": record_data.doctor_name,
        "doctor_id": record_data.doctor_id,
        "appointment_id": record_data.appointment_id,
        "prescription_id": record_data.prescription_id,
        "vital_signs": (
            record_data.vital_signs.model_dump() if record_data.vital_signs else None
        ),
        "symptoms": record_data.symptoms,
        "diagnosis_codes": record_data.diagnosis_codes,
        "attachments": [],
        "meta": {"created_by": "prescription-service"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = db.medical_records.insert_one(record_dict)
    record_dict["_id"] = result.inserted_id

    logger.info("medical_record_created", record_id=record_id)

    # Publish event
    publish_event_sync(
        "medical_record.created",
        {
            "record_id": record_id,
            "patient_id": record_data.patient_id,
            "record_type": record_data.record_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return models.MedicalRecord(**record_dict)


def get_medical_record_by_id(db: Database, record_id: str) -> models.MedicalRecord:
    """
    Get medical record by ID.

    :param db: MongoDB database
    :param record_id: Record identifier
    :return: Medical record object
    :raises ResourceNotFoundError: If record not found
    """
    record = db.medical_records.find_one({"record_id": record_id})

    if not record:
        raise ResourceNotFoundError("Medical Record", record_id)

    return models.MedicalRecord(**record)


def get_medical_records_by_patient(
    db: Database, patient_id: str, skip: int = 0, limit: int = 100
) -> List[models.MedicalRecord]:
    """
    Get all medical records for a patient.

    :param db: MongoDB database
    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: List of medical records
    """
    records = (
        db.medical_records.find({"patient_id": patient_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    return [models.MedicalRecord(**r) for r in records]


def update_medical_record(
    db: Database, record_id: str, record_data: schemas.MedicalRecordUpdate
) -> models.MedicalRecord:
    """
    Update medical record.

    :param db: MongoDB database
    :param record_id: Record identifier
    :param record_data: Record update data
    :return: Updated medical record
    """
    _ = get_medical_record_by_id(db, record_id)

    update_dict = {"updated_at": datetime.now(timezone.utc)}

    if record_data.title:
        update_dict["title"] = record_data.title

    if record_data.description:
        update_dict["description"] = record_data.description

    if record_data.vital_signs:
        update_dict["vital_signs"] = record_data.vital_signs.model_dump()

    db.medical_records.update_one({"record_id": record_id}, {"$set": update_dict})

    logger.info("medical_record_updated", record_id=record_id)

    return get_medical_record_by_id(db, record_id)


# ============================================
# Lab Result Service Functions
# ============================================


def generate_lab_result_id() -> str:
    """Generate unique lab result ID."""
    return f"LAB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def create_lab_result(
    db: Database, result_data: schemas.LabResultCreate
) -> models.LabResult:
    """
    Create new lab result.

    :param db: MongoDB database
    :param result_data: Lab result creation data
    :return: Created lab result
    """
    logger.info("creating_lab_result", patient_id=result_data.patient_id)

    result_id = generate_lab_result_id()

    result_dict = {
        "result_id": result_id,
        "patient_id": result_data.patient_id,
        "test_name": result_data.test_panel_name,
        "test_panel_name": result_data.test_panel_name,
        "test_category": result_data.test_category,
        "tests": [test.model_dump() for test in result_data.tests],
        "ordering_doctor": result_data.ordering_doctor,
        "performing_lab": result_data.performing_lab,
        "test_date": result_data.test_date,
        "result_date": result_data.result_date,
        "status": models.LabResultStatus.PRELIMINARY.value,
        "interpretation": result_data.interpretation,
        "critical_results": result_data.critical_results,
        "appointment_id": result_data.appointment_id,
        "prescription_id": result_data.prescription_id,
        "attachments": [],
        "meta": {"created_by": "prescription-service"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = db.lab_results.insert_one(result_dict)
    result_dict["_id"] = result.inserted_id

    logger.info("lab_result_created", result_id=result_id)

    # Publish event
    publish_event_sync(
        "lab_result.created",
        {
            "result_id": result_id,
            "patient_id": result_data.patient_id,
            "test_panel_name": result_data.test_panel_name,
            "critical_results": result_data.critical_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return models.LabResult(**result_dict)


def get_lab_result_by_id(db: Database, result_id: str) -> models.LabResult:
    """
    Get lab result by ID.

    :param db: MongoDB database
    :param result_id: Result identifier
    :return: Lab result object
    :raises ResourceNotFoundError: If result not found
    """
    result = db.lab_results.find_one({"result_id": result_id})

    if not result:
        raise ResourceNotFoundError("Lab Result", result_id)

    return models.LabResult(**result)


def get_lab_results_by_patient(
    db: Database, patient_id: str, skip: int = 0, limit: int = 100
) -> List[models.LabResult]:
    """
    Get all lab results for a patient.

    :param db: MongoDB database
    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: List of lab results
    """
    results = (
        db.lab_results.find({"patient_id": patient_id})
        .sort("result_date", -1)
        .skip(skip)
        .limit(limit)
    )

    return [models.LabResult(**r) for r in results]


def update_lab_result(
    db: Database, result_id: str, result_data: schemas.LabResultUpdate
) -> models.LabResult:
    """
    Update lab result.

    :param db: MongoDB database
    :param result_id: Result identifier
    :param result_data: Result update data
    :return: Updated lab result
    """
    _ = get_lab_result_by_id(db, result_id)

    update_dict = {"updated_at": datetime.now(timezone.utc)}

    if result_data.status:
        update_dict["status"] = result_data.status.value

    if result_data.interpretation:
        update_dict["interpretation"] = result_data.interpretation

    db.lab_results.update_one({"result_id": result_id}, {"$set": update_dict})

    logger.info("lab_result_updated", result_id=result_id)

    return get_lab_result_by_id(db, result_id)
