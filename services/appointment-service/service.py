"""
Business Logic Layer for Appointment Service.

This module contains all business logic for appointment management.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

import models
import schemas
from common.exceptions import (
    AppointmentNotFoundError,
    PatientNotFoundError,
    ServiceUnavailableError,
)
from common.logging import get_logger
from common.utils import retry_on_api_error
from config import get_settings


settings = get_settings()
logger = get_logger(__name__)


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


def create_appointment(
    db: Session, appointment_data: schemas.AppointmentCreate
) -> models.Appointment:
    """
    Create new appointment.

    :param db: Database session
    :param appointment_data: Appointment creation data
    :return: Created appointment
    :raises ValidationError: If validation fails
    """
    logger.info("creating_appointment", patient_id=appointment_data.patient_id)

    minute_duration = appointment_data.minute_duration
    if not minute_duration:
        minute_duration = int(
            (appointment_data.end - appointment_data.start).total_seconds() / 60
        )

    participant_data = [
        {
            "type": ["patient"],
            "actor": appointment_data.patient_id,
            "required": "required",
            "status": "accepted",
        }
    ]

    if appointment_data.practitioner_id:
        participant_data.append(
            {
                "type": ["practitioner"],
                "actor": appointment_data.practitioner_id,
                "required": "required",
                "status": "accepted",
            }
        )

    appointment = models.Appointment(
        status=appointment_data.status.value,
        service_category=appointment_data.service_category,
        service_type=appointment_data.service_type,
        specialty=appointment_data.specialty,
        appointment_type=appointment_data.appointment_type,
        reason_code=appointment_data.reason_code,
        reason_reference=appointment_data.reason_reference,
        priority=appointment_data.priority,
        description=appointment_data.description,
        start=appointment_data.start,
        end=appointment_data.end,
        minute_duration=minute_duration,
        slot=appointment_data.slot,
        created=appointment_data.created or datetime.utcnow(),
        comment=appointment_data.comment,
        requested_period=appointment_data.requested_period,
        participant=participant_data,
        location=appointment_data.location,
        identifier=appointment_data.identifier,
        meta={"created_by": "appointment-service"},
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    logger.info("appointment_created", appointment_id=str(appointment.id))

    return appointment


def get_appointment_by_id(db: Session, appointment_id: str) -> models.Appointment:
    """
    Get appointment by ID.

    :param db: Database session
    :param appointment_id: Appointment identifier
    :return: Appointment
    :raises AppointmentNotFoundError: If appointment not found
    """
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == uuid.UUID(appointment_id))
        .first()
    )

    if not appointment:
        raise AppointmentNotFoundError(appointment_id)

    return appointment


def list_appointments(
    db: Session,
    patient_id: Optional[str] = None,
    practitioner_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[models.Appointment], int]:
    """
    List appointments with filters.

    :param db: Database session
    :param patient_id: Patient identifier
    :param practitioner_id: Practitioner identifier
    :param status: Appointment status
    :param start_date: Start date filter
    :param end_date: End date filter
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :return: Tuple of (appointments list, total count)
    """
    query = db.query(models.Appointment)

    if patient_id:
        query = query.filter(
            models.Appointment.participant.op("@>")(
                func.cast([{"actor": patient_id}], JSONB)
            )
        )

    if practitioner_id:
        query = query.filter(
            models.Appointment.participant.op("@>")(
                func.cast([{"actor": practitioner_id}], JSONB)
            )
        )

    if status:
        query = query.filter(models.Appointment.status == status)

    if start_date:
        query = query.filter(models.Appointment.start >= start_date)

    if end_date:
        query = query.filter(models.Appointment.end <= end_date)

    total = query.count()
    appointments = query.offset(skip).limit(limit).all()

    return appointments, total


def update_appointment(
    db: Session, appointment_id: str, appointment_update: schemas.AppointmentUpdate
) -> models.Appointment:
    """
    Update appointment.

    :param db: Database session
    :param appointment_id: Appointment identifier
    :param appointment_update: Appointment update data
    :return: Updated appointment
    :raises AppointmentNotFoundError: If appointment not found
    """
    appointment = get_appointment_by_id(db, appointment_id)

    update_data = appointment_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(appointment, field):
            if isinstance(value, schemas.AppointmentStatusEnum):
                setattr(appointment, field, value.value)
            else:
                setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    logger.info("appointment_updated", appointment_id=appointment_id)

    return appointment


def delete_appointment(db: Session, appointment_id: str) -> None:
    """
    Delete appointment.

    :param db: Database session
    :param appointment_id: Appointment identifier
    :raises AppointmentNotFoundError: If appointment not found
    """
    appointment = get_appointment_by_id(db, appointment_id)

    db.delete(appointment)
    db.commit()

    logger.info("appointment_deleted", appointment_id=appointment_id)


def cancel_appointment(db: Session, appointment_id: str) -> models.Appointment:
    """
    Cancel appointment.

    :param db: Database session
    :param appointment_id: Appointment identifier
    :return: Cancelled appointment
    :raises AppointmentNotFoundError: If appointment not found
    """
    appointment = get_appointment_by_id(db, appointment_id)

    appointment.status = schemas.AppointmentStatusEnum.CANCELLED.value
    appointment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(appointment)

    logger.info("appointment_cancelled", appointment_id=appointment_id)

    return appointment
