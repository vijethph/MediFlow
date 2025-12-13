"""
Business Logic Layer for Patient Service.

This module contains all business logic for patient management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from common.exceptions import (
    DuplicateResourceError,
    PatientNotFoundError,
    ValidationError,
)
from common.logging import get_logger
from common.messaging import publish_event
from config import get_settings


settings = get_settings()
logger = get_logger(__name__)


def generate_patient_id() -> str:
    """
    Generate unique patient ID in format PAT-XXXXX.

    :return: Generated patient ID
    """
    unique_id = str(uuid.uuid4()).replace("-", "").upper()[:8]
    return f"PAT-{unique_id}"


def create_access_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    """
    Create JWT access token for patient authentication.

    :param data: Payload data to encode in token
    :param expires_delta: Token expiration time delta
    :return: Encoded JWT token
    """
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "sub": data.get("patient_id", "")})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_patient(db: Session, patient_data: schemas.PatientCreate) -> models.Patient:
    """
    Create a new patient record.

    :param db: Database session
    :param patient_data: Patient creation data
    :return: Created patient
    :raises DuplicateResourceError: If email already exists
    """
    patient_id = generate_patient_id()

    email = None
    if patient_data.telecom:
        for contact in patient_data.telecom:
            if contact.system == schemas.ContactPointSystemEnum.EMAIL:
                email = contact.value
                break

    if email:
        existing_patient = get_patient_by_email(db, email)
        if existing_patient:
            raise DuplicateResourceError("Patient", f"email={email}")

    db_patient = models.Patient(
        patient_id=patient_id,
        resource_type="Patient",
        active=True,
        name=[n.model_dump() for n in patient_data.name],
        telecom=(
            [t.model_dump() for t in patient_data.telecom]
            if patient_data.telecom
            else None
        ),
        gender=patient_data.gender.value if patient_data.gender else None,
        birth_date=patient_data.birth_date,
        address=(
            [a.model_dump() for a in patient_data.address]
            if patient_data.address
            else None
        ),
        marital_status=patient_data.marital_status,
        multiple_births_integer=(
            str(patient_data.multiple_births_integer)
            if patient_data.multiple_births_integer
            else None
        ),
        contact=patient_data.contact,
        communication=patient_data.communication,
        general_practitioner=patient_data.general_practitioner,
        managing_organization=patient_data.managing_organization,
        meta={
            "versionId": "1",
            "lastUpdated": datetime.utcnow().isoformat(),
        },
    )

    try:
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)

        logger.info("patient_created", patient_id=patient_id)

        publish_event(
            "patient.created",
            {
                "patient_id": patient_id,
                "resource_type": "Patient",
                "created_at": db_patient.created_at.isoformat(),
            },
        )

        return db_patient

    except IntegrityError as e:
        db.rollback()
        logger.error("patient_creation_failed", error=str(e))
        raise DuplicateResourceError("Patient", "unique constraint violation") from e


def get_patient_by_id(db: Session, patient_id: str) -> models.Patient:
    """
    Get patient by patient_id.

    :param db: Database session
    :param patient_id: Patient identifier
    :return: Patient record
    :raises PatientNotFoundError: If patient not found
    """
    patient = (
        db.query(models.Patient)
        .filter(models.Patient.patient_id == patient_id, models.Patient.active == True)
        .first()
    )

    if not patient:
        raise PatientNotFoundError(patient_id)

    return patient


def get_patient_by_email(db: Session, email: str) -> Optional[models.Patient]:
    """
    Get patient by email address.

    :param db: Database session
    :param email: Email address
    :return: Patient record or None
    """
    patients = db.query(models.Patient).filter(models.Patient.active == True).all()

    for patient in patients:
        if patient.telecom:
            for contact in patient.telecom:
                if contact.get("system") == "email" and contact.get("value") == email:
                    return patient

    return None


def get_patients(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[List[models.Patient], int]:
    """
    Get list of active patients with pagination.

    :param db: Database session
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: Tuple of (list of patients, total count)
    """
    query = db.query(models.Patient).filter(models.Patient.active == True)

    total = query.count()

    patients = (
        query.order_by(models.Patient.created_at.desc()).offset(skip).limit(limit).all()
    )

    return patients, total


def update_patient(
    db: Session, patient_id: str, patient_update: schemas.PatientUpdate
) -> models.Patient:
    """
    Update patient information.

    :param db: Database session
    :param patient_id: Patient identifier
    :param patient_update: Patient update data
    :return: Updated patient
    :raises PatientNotFoundError: If patient not found
    """
    db_patient = get_patient_by_id(db, patient_id)

    update_data = patient_update.model_dump(exclude_unset=True)

    if not update_data:
        return db_patient

    if patient_update.name is not None:
        db_patient.name = [n.model_dump() for n in patient_update.name]

    if patient_update.telecom is not None:
        db_patient.telecom = [t.model_dump() for t in patient_update.telecom]

    if patient_update.gender is not None:
        db_patient.gender = patient_update.gender.value

    if patient_update.birth_date is not None:
        db_patient.birth_date = patient_update.birth_date

    if patient_update.address is not None:
        db_patient.address = [a.model_dump() for a in patient_update.address]

    if patient_update.marital_status is not None:
        db_patient.marital_status = patient_update.marital_status

    db_patient.updated_at = datetime.utcnow()
    db_patient.meta = {
        **db_patient.meta,
        "versionId": str(int(db_patient.meta.get("versionId", 1)) + 1),
        "lastUpdated": datetime.utcnow().isoformat(),
    }

    try:
        db.commit()
        db.refresh(db_patient)

        logger.info("patient_updated", patient_id=patient_id)

        publish_event(
            "patient.updated",
            {
                "patient_id": patient_id,
                "resource_type": "Patient",
                "updated_at": db_patient.updated_at.isoformat(),
            },
        )

        return db_patient

    except IntegrityError as e:
        db.rollback()
        logger.error("patient_update_failed", error=str(e), patient_id=patient_id)
        raise ValidationError(f"Patient update failed: {str(e)}") from e


def delete_patient(db: Session, patient_id: str) -> bool:
    """
    Soft delete patient (set active=False).

    :param db: Database session
    :param patient_id: Patient identifier
    :return: True if deleted
    :raises PatientNotFoundError: If patient not found
    """
    db_patient = get_patient_by_id(db, patient_id)

    db_patient.active = False
    db_patient.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_patient)

    logger.info("patient_deleted", patient_id=patient_id)

    publish_event(
        "patient.deleted",
        {
            "patient_id": patient_id,
            "resource_type": "Patient",
            "deleted_at": db_patient.updated_at.isoformat(),
        },
    )

    return True


def count_active_patients(db: Session) -> int:
    """
    Count total number of active patients.

    :param db: Database session
    :return: Number of active patients
    """
    return db.query(models.Patient).filter(models.Patient.active == True).count()


def authenticate_patient(db: Session, email: str) -> tuple[models.Patient, str]:
    """
    Authenticate patient and generate JWT token.

    :param db: Database session
    :param email: Patient email address
    :return: Tuple of (patient, access_token)
    :raises PatientNotFoundError: If patient not found or inactive
    """
    db_patient = get_patient_by_email(db, email)

    if not db_patient:
        raise PatientNotFoundError(f"email={email}")

    if not db_patient.active:
        raise ValidationError("Patient account is inactive")

    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"patient_id": db_patient.patient_id, "email": email},
        expires_delta=access_token_expires,
    )

    logger.info("patient_authenticated", patient_id=db_patient.patient_id)

    return db_patient, access_token
