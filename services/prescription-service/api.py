"""
API Routes for Prescription Service.

This module defines REST API endpoints for prescriptions, medical records, and lab results.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pymongo.database import Database

import schemas
import service
from common.exceptions import (
    PatientNotFoundError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from common.logging import get_logger
from database import get_db
from dependencies import require_authentication

router = APIRouter()
logger = get_logger(__name__)


# ============================================
# Prescription Endpoints
# ============================================


@router.post(
    "/prescriptions",
    response_model=schemas.PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Prescriptions"],
    summary="Create a new prescription",
)
async def create_prescription(
    prescription_data: schemas.PrescriptionCreate,
    current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Create a new prescription for a patient.

    :param prescription_data: Prescription creation data
    :param request: FastAPI request object
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created prescription
    """
    logger.info(
        "api_create_prescription",
        patient_id=prescription_data.patient_id,
        user_id=current_user.get("sub"),
    )

    try:
        prescription = service.create_prescription(db, prescription_data)

        response_dict = prescription.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.PrescriptionResponse(**response_dict)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=schemas.PrescriptionResponse,
    tags=["Prescriptions"],
    summary="Get prescription by ID",
)
def get_prescription(
    prescription_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Retrieve prescription by ID.

    :param prescription_id: Prescription identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Prescription details
    """
    logger.info("api_get_prescription", prescription_id=prescription_id)

    try:
        prescription = service.get_prescription_by_id(db, prescription_id)

        response_dict = prescription.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.PrescriptionResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/prescriptions",
    response_model=schemas.PrescriptionListResponse,
    tags=["Prescriptions"],
    summary="List prescriptions by patient",
)
def list_prescriptions(
    patient_id: str = Query(..., description="Patient ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    List all prescriptions for a patient.

    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of prescriptions
    """
    logger.info("api_list_prescriptions", patient_id=patient_id, skip=skip, limit=limit)

    prescriptions = service.get_prescriptions_by_patient(db, patient_id, skip, limit)

    prescription_responses = []
    for prescription in prescriptions:
        response_dict = prescription.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])
        prescription_responses.append(schemas.PrescriptionResponse(**response_dict))

    return schemas.PrescriptionListResponse(
        total=len(prescription_responses),
        prescriptions=prescription_responses,
    )


@router.put(
    "/prescriptions/{prescription_id}",
    response_model=schemas.PrescriptionResponse,
    tags=["Prescriptions"],
    summary="Update prescription",
)
def update_prescription(
    prescription_id: str,
    prescription_update: schemas.PrescriptionUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Update prescription details.

    :param prescription_id: Prescription identifier
    :param prescription_update: Prescription update data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated prescription
    """
    logger.info("api_update_prescription", prescription_id=prescription_id)

    try:
        prescription = service.update_prescription(
            db, prescription_id, prescription_update
        )

        response_dict = prescription.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.PrescriptionResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============================================
# Medical Record Endpoints
# ============================================


@router.post(
    "/medical-records",
    response_model=schemas.MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Medical Records"],
    summary="Create a new medical record",
)
async def create_medical_record(
    record_data: schemas.MedicalRecordCreate,
    current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Create a new medical record for a patient.

    :param record_data: Medical record creation data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created medical record
    """
    logger.info(
        "api_create_medical_record",
        patient_id=record_data.patient_id,
        user_id=current_user.get("sub"),
    )

    try:
        record = service.create_medical_record(db, record_data)

        response_dict = record.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.MedicalRecordResponse(**response_dict)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/medical-records/{record_id}",
    response_model=schemas.MedicalRecordResponse,
    tags=["Medical Records"],
    summary="Get medical record by ID",
)
def get_medical_record(
    record_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Retrieve medical record by ID.

    :param record_id: Record identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Medical record details
    """
    logger.info("api_get_medical_record", record_id=record_id)

    try:
        record = service.get_medical_record_by_id(db, record_id)

        response_dict = record.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.MedicalRecordResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/medical-records",
    response_model=schemas.MedicalRecordListResponse,
    tags=["Medical Records"],
    summary="List medical records by patient",
)
def list_medical_records(
    patient_id: str = Query(..., description="Patient ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    List all medical records for a patient.

    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of medical records
    """
    logger.info(
        "api_list_medical_records", patient_id=patient_id, skip=skip, limit=limit
    )

    records = service.get_medical_records_by_patient(db, patient_id, skip, limit)

    record_responses = []
    for record in records:
        response_dict = record.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])
        record_responses.append(schemas.MedicalRecordResponse(**response_dict))

    return schemas.MedicalRecordListResponse(
        total=len(record_responses),
        records=record_responses,
    )


@router.put(
    "/medical-records/{record_id}",
    response_model=schemas.MedicalRecordResponse,
    tags=["Medical Records"],
    summary="Update medical record",
)
def update_medical_record(
    record_id: str,
    record_update: schemas.MedicalRecordUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Update medical record.

    :param record_id: Record identifier
    :param record_update: Record update data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated medical record
    """
    logger.info("api_update_medical_record", record_id=record_id)

    try:
        record = service.update_medical_record(db, record_id, record_update)

        response_dict = record.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.MedicalRecordResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============================================
# Lab Result Endpoints
# ============================================


@router.post(
    "/lab-results",
    response_model=schemas.LabResultResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Lab Results"],
    summary="Create new lab result",
)
async def create_lab_result(
    result_data: schemas.LabResultCreate,
    current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Create new lab result for a patient.

    :param result_data: Lab result creation data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created lab result
    """
    logger.info(
        "api_create_lab_result",
        patient_id=result_data.patient_id,
        user_id=current_user.get("sub"),
    )

    try:
        result = service.create_lab_result(db, result_data)

        response_dict = result.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.LabResultResponse(**response_dict)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/lab-results/{result_id}",
    response_model=schemas.LabResultResponse,
    tags=["Lab Results"],
    summary="Get lab result by ID",
)
def get_lab_result(
    result_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Retrieve lab result by ID.

    :param result_id: Result identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Lab result details
    """
    logger.info("api_get_lab_result", result_id=result_id)

    try:
        result = service.get_lab_result_by_id(db, result_id)

        response_dict = result.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.LabResultResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/lab-results",
    response_model=schemas.LabResultListResponse,
    tags=["Lab Results"],
    summary="List lab results by patient",
)
def list_lab_results(
    patient_id: str = Query(..., description="Patient ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    List all lab results for a patient.

    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of lab results
    """
    logger.info("api_list_lab_results", patient_id=patient_id, skip=skip, limit=limit)

    results = service.get_lab_results_by_patient(db, patient_id, skip, limit)

    result_responses = []
    for result in results:
        response_dict = result.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])
        result_responses.append(schemas.LabResultResponse(**response_dict))

    return schemas.LabResultListResponse(
        total=len(result_responses),
        results=result_responses,
    )


@router.put(
    "/lab-results/{result_id}",
    response_model=schemas.LabResultResponse,
    tags=["Lab Results"],
    summary="Update lab result",
)
def update_lab_result(
    result_id: str,
    result_update: schemas.LabResultUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Database = Depends(get_db),
):
    """
    Update lab result.

    :param result_id: Result identifier
    :param result_update: Result update data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated lab result
    """
    logger.info("api_update_lab_result", result_id=result_id)

    try:
        result = service.update_lab_result(db, result_id, result_update)

        response_dict = result.model_dump(by_alias=True)
        response_dict["_id"] = str(response_dict["_id"])

        return schemas.LabResultResponse(**response_dict)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
