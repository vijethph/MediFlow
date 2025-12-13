"""
API Routes for Appointment Service.

This module defines REST API endpoints for appointment management.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import schemas
import service
from common.exceptions import (
    AppointmentNotFoundError,
    PatientNotFoundError,
    ValidationError,
)
from common.logging import get_logger
from database import get_db
from dependencies import require_authentication


router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/appointments",
    response_model=schemas.AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
)
async def create_appointment(
    appointment_data: schemas.AppointmentCreate,
    request: Request,
    current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Create a new appointment for a patient.

    :param appointment_data: Appointment creation data
    :param request: FastAPI request object
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created appointment
    """
    logger.info(
        "api_create_appointment",
        patient_id=appointment_data.patient_id,
        user_id=current_user.get("sub"),
    )

    try:
        auth_header = request.headers.get("Authorization", "")
        jwt_token = (
            auth_header.replace("Bearer ", "")
            if auth_header.startswith("Bearer ")
            else ""
        )
        if jwt_token:
            await service.verify_patient_exists(appointment_data.patient_id, jwt_token)

        appointment = service.create_appointment(db, appointment_data)
        return schemas.AppointmentResponse.from_orm(appointment)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get(
    "/appointments/{appointment_id}",
    response_model=schemas.AppointmentResponse,
    summary="Get appointment by ID",
)
def get_appointment(
    appointment_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Retrieve appointment by ID.

    :param appointment_id: Appointment identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Appointment details
    """
    logger.info("api_get_appointment", appointment_id=appointment_id)

    try:
        appointment = service.get_appointment_by_id(db, appointment_id)
        return schemas.AppointmentResponse.from_orm(appointment)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/appointments",
    response_model=schemas.AppointmentList,
    summary="List appointments",
)
def list_appointments(
    patient_id: str = Query(None, description="Patient ID"),
    practitioner_id: str = Query(None, description="Practitioner ID"),
    appointment_status: str = Query(None, description="Appointment status"),
    start_date: datetime = Query(None, description="Start date filter"),
    end_date: datetime = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List appointments with optional filters.

    :param patient_id: Patient identifier
    :param practitioner_id: Practitioner identifier
    :param appointment_status: Appointment status
    :param start_date: Start date filter
    :param end_date: End date filter
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of appointments
    """
    logger.info(
        "api_list_appointments",
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        skip=skip,
        limit=limit,
    )

    appointments, total = service.list_appointments(
        db,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        status=appointment_status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )

    return schemas.AppointmentList(
        total=total,
        count=len(appointments),
        skip=skip,
        limit=limit,
        items=[schemas.AppointmentResponse.from_orm(apt) for apt in appointments],
    )


@router.put(
    "/appointments/{appointment_id}",
    response_model=schemas.AppointmentResponse,
    summary="Update appointment",
)
def update_appointment(
    appointment_id: str,
    appointment_update: schemas.AppointmentUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Update appointment details.

    :param appointment_id: Appointment identifier
    :param appointment_update: Appointment update data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated appointment
    """
    logger.info("api_update_appointment", appointment_id=appointment_id)

    try:
        appointment = service.update_appointment(db, appointment_id, appointment_update)
        return schemas.AppointmentResponse.from_orm(appointment)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete(
    "/appointments/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appointment",
)
def delete_appointment(
    appointment_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Delete an appointment.

    :param appointment_id: Appointment identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    """
    logger.info("api_delete_appointment", appointment_id=appointment_id)

    try:
        service.delete_appointment(db, appointment_id)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=schemas.AppointmentResponse,
    summary="Cancel appointment",
)
def cancel_appointment(
    appointment_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Cancel an appointment (update status to cancelled).

    :param appointment_id: Appointment identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Cancelled appointment
    """
    logger.info("api_cancel_appointment", appointment_id=appointment_id)

    try:
        appointment = service.cancel_appointment(db, appointment_id)
        return schemas.AppointmentResponse.from_orm(appointment)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
