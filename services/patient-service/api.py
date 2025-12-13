"""
API Routes for Patient Service.

This module defines REST API endpoints for patient management.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import schemas
import service
from common.exceptions import (
    DuplicateResourceError,
    PatientNotFoundError,
    ValidationError,
)
from common.logging import get_logger
from database import get_db
from dependencies import require_authentication


router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/register",
    response_model=schemas.Token,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register a new patient",
)
def register_patient(
    patient_data: schemas.PatientCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new patient and return JWT token.

    :param patient_data: Patient creation data
    :param db: Database session
    :return: JWT token with patient details
    """
    logger.info("api_register_patient")

    try:
        patient = service.create_patient(db, patient_data)

        email = None
        if patient.telecom:
            for contact in patient.telecom:
                if contact.get("system") == "email":
                    email = contact.get("value")
                    break

        if not email:
            raise ValidationError("Patient must have an email address")

        access_token = service.create_access_token(
            data={"patient_id": patient.patient_id, "email": email},
            expires_delta=service.timedelta(
                minutes=service.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            ),
        )

        return schemas.Token(
            access_token=access_token,
            token_type="bearer",
            patient_id=patient.patient_id,
            email=email,
        )

    except DuplicateResourceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post(
    "/login",
    response_model=schemas.Token,
    tags=["Authentication"],
    summary="Login patient",
)
def login_patient(
    login_data: schemas.PatientLogin,
    db: Session = Depends(get_db),
):
    """
    Authenticate patient and return JWT token.

    :param login_data: Login credentials
    :param db: Database session
    :return: JWT token with patient details
    """
    logger.info("api_login_patient", email=login_data.email)

    try:
        patient, access_token = service.authenticate_patient(db, login_data.email)

        return schemas.Token(
            access_token=access_token,
            token_type="bearer",
            patient_id=patient.patient_id,
            email=login_data.email,
        )

    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/{patient_id}",
    response_model=schemas.PatientResponse,
    tags=["Patients"],
    summary="Get patient by ID",
)
def get_patient(
    patient_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Retrieve patient by ID.

    :param patient_id: Patient identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Patient details
    """
    logger.info("api_get_patient", patient_id=patient_id)

    try:
        patient = service.get_patient_by_id(db, patient_id)

        return convert_patient_to_response(patient)

    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/",
    response_model=schemas.PatientList,
    tags=["Patients"],
    summary="List all patients",
)
def list_patients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List all active patients with pagination.

    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of patients
    """
    logger.info("api_list_patients", skip=skip, limit=limit)

    patients, total = service.get_patients(db, skip=skip, limit=limit)

    return schemas.PatientList(
        total=total,
        count=len(patients),
        skip=skip,
        limit=limit,
        items=[convert_patient_to_response(p) for p in patients],
    )


@router.put(
    "/{patient_id}",
    response_model=schemas.PatientResponse,
    tags=["Patients"],
    summary="Update patient",
)
def update_patient(
    patient_id: str,
    patient_update: schemas.PatientUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Update patient information.

    :param patient_id: Patient identifier
    :param patient_update: Patient update data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated patient details
    """
    logger.info("api_update_patient", patient_id=patient_id)

    try:
        patient = service.update_patient(db, patient_id, patient_update)

        return convert_patient_to_response(patient)

    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Patients"],
    summary="Delete patient",
)
def delete_patient(
    patient_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Soft delete patient (set active=False).

    :param patient_id: Patient identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: None
    """
    logger.info("api_delete_patient", patient_id=patient_id)

    try:
        service.delete_patient(db, patient_id)

        return None

    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


def convert_patient_to_response(patient) -> schemas.PatientResponse:
    """
    Convert Patient model to PatientResponse schema.

    :param patient: Patient database model
    :return: PatientResponse schema
    """
    email = None
    if patient.telecom:
        for contact in patient.telecom:
            if contact.get("system") == "email":
                email = contact.get("value")
                break

    return schemas.PatientResponse(
        id=patient.patient_id,
        resource_type=patient.resource_type,
        identifier=[
            schemas.Identifier(
                system="http://hospital.org/patient-id", value=patient.patient_id
            )
        ],
        active=patient.active,
        name=[schemas.HumanName(**n) for n in patient.name] if patient.name else [],
        telecom=(
            [schemas.ContactPoint(**t) for t in patient.telecom]
            if patient.telecom
            else None
        ),
        gender=schemas.GenderEnum(patient.gender) if patient.gender else None,
        birth_date=patient.birth_date,
        address=(
            [schemas.Address(**a) for a in patient.address] if patient.address else None
        ),
        marital_status=patient.marital_status,
        contact=patient.contact,
        general_practitioner=patient.general_practitioner,
        managing_organization=patient.managing_organization,
        meta=patient.meta or {},
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )
