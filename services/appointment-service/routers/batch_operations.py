"""Batch operations for appointments."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from prometheus_client import Counter
# Metrics defined in main.py

from database import get_db
from schemas import AppointmentCreate, Appointment
from service import create_appointment, check_doctor_availability
from dependencies import get_current_user
from rate_limit import limiter
from config import Settings
settings = Settings()
from cache import delete_cache_pattern
from fastapi import BackgroundTasks

router = APIRouter(prefix="/api/v1/appointments", tags=["batch-operations"])



@router.post("/batch/create", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def batch_create_appointments(
    request: Request,
    appointments: List[AppointmentCreate],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple appointments in a single request.
    
    Validates all appointments before creating any.
    """
    if len(appointments) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 appointments per batch"
        )
    
    created_appointments = []
    failed_appointments = []
    
    # Validate all appointments first
    for idx, appointment in enumerate(appointments):
        try:
            # Check availability
            is_available = await check_doctor_availability(
                db=db,
                doctor_id=appointment.doctor_id,
                appointment_date=appointment.appointment_date,
                duration_minutes=appointment.duration_minutes
            )
            
            if not is_available:
                failed_appointments.append({
                    "index": idx,
                    "error": "Doctor not available",
                    "appointment": appointment.model_dump()
                })
                continue
            
            # Create appointment
            created_by = current_user.get("email") or current_user.get("user_id")
            db_appointment = await create_appointment(db, appointment, created_by=created_by)
            created_appointments.append(Appointment.model_validate(db_appointment).model_dump())
            
        except Exception as e:
            failed_appointments.append({
                "index": idx,
                "error": str(e),
                "appointment": appointment.model_dump()
            })
    
    # Invalidate cache
    if created_appointments:
        background_tasks.add_task(delete_cache_pattern, "appointment:*")
    
    request_count.labels(operation='batch_create', status='201').inc()
    
    return {
        "created": len(created_appointments),
        "failed": len(failed_appointments),
        "appointments": created_appointments,
        "failures": failed_appointments
    }


@router.post("/batch/cancel", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def batch_cancel_appointments(
    request: Request,
    appointment_ids: List[str],
    background_tasks: BackgroundTasks,
    cancellation_reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel multiple appointments in a single request.
    """
    if len(appointment_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 appointments per batch"
        )
    
    from service import cancel_appointment
    
    cancelled_appointments = []
    failed_appointments = []
    cancelled_by = current_user.get("email") or current_user.get("user_id")
    
    for appointment_id in appointment_ids:
        try:
            db_appointment = await cancel_appointment(
                db=db,
                appointment_id=appointment_id,
                cancellation_reason=cancellation_reason,
                cancelled_by=cancelled_by
            )
            
            if db_appointment:
                cancelled_appointments.append(appointment_id)
            else:
                failed_appointments.append({
                    "appointment_id": appointment_id,
                    "error": "Appointment not found"
                })
        except Exception as e:
            failed_appointments.append({
                "appointment_id": appointment_id,
                "error": str(e)
            })
    
    # Invalidate cache
    if cancelled_appointments:
        background_tasks.add_task(delete_cache_pattern, "appointment:*")
    
    request_count.labels(operation='batch_cancel', status='200').inc()
    
    return {
        "cancelled": len(cancelled_appointments),
        "failed": len(failed_appointments),
        "appointment_ids": cancelled_appointments,
        "failures": failed_appointments
    }

