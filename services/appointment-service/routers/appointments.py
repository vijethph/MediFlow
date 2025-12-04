"""Appointment API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timedelta
from prometheus_client import Gauge

from database import get_db
from schemas import (
    Appointment,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentCancel,
    AppointmentReschedule,
    HealthCheck
)
from service import (
    create_appointment,
    get_appointment,
    get_appointments_by_patient,
    get_appointments_by_doctor,
    get_appointments,
    update_appointment,
    cancel_appointment,
    check_doctor_availability,
    get_upcoming_appointments,
    count_appointments_by_status
)
from models import AppointmentStatus
from dependencies import get_current_user
from config import Settings
settings = Settings()
from cache import get_cache, set_cache, delete_cache_pattern
from rate_limit import limiter
from background_tasks import invalidate_appointment_cache, send_appointment_notification
from retry import retry_with_backoff, RetryConfig
from fastapi import BackgroundTasks

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

# Prometheus metrics (only unique ones - request_count and request_duration are in main.py)
active_appointments_gauge = Gauge(
    'appointment_service_active_appointments',
    'Number of active appointments'
)


@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
async def create_appointment_endpoint(
    appointment: AppointmentCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new appointment.
    
    Checks doctor availability and creates appointment if available.
    Uses caching and retry mechanisms for reliability.
    """
    try:
        # Check cache for availability (if recently checked)
        availability_cache_key = f"appointment:availability:{appointment.doctor_id}:{appointment.appointment_date.isoformat()}"
        cached_availability = await get_cache(availability_cache_key)
        
        if cached_availability is not None:
            is_available = cached_availability
        else:
            # Check doctor availability with retry
            retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
            is_available = await retry_with_backoff(
                check_doctor_availability,
                db=db,
                doctor_id=appointment.doctor_id,
                appointment_date=appointment.appointment_date,
                duration_minutes=appointment.duration_minutes,
                config=retry_config
            )
            # Cache availability result for 5 minutes
            await set_cache(availability_cache_key, is_available, ttl=300)
        
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor is not available at the requested time"
            )
        
        # Create appointment with retry
        retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
        created_by = current_user.get("email") or current_user.get("user_id")
        db_appointment = await retry_with_backoff(
            create_appointment,
            db=db,
            appointment=appointment,
            created_by=created_by,
            config=retry_config
        )
        
        # Invalidate cache
        background_tasks.add_task(
            invalidate_appointment_cache,
            appointment_id=db_appointment.appointment_id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id
        )
        
        # Send notification (background task)
        background_tasks.add_task(
            send_appointment_notification,
            appointment_id=db_appointment.appointment_id,
            notification_type="created",
            data={"appointment": db_appointment.appointment_id, "patient_id": appointment.patient_id}
        )
        
        # Update metrics
        active_appointments_gauge.inc()
        
        return db_appointment
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment conflict detected"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{appointment_id}", response_model=Appointment)
@limiter.limit("1000/hour")
async def get_appointment_endpoint(
    appointment_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get appointment by ID with caching."""
    # Try cache first
    cache_key = f"appointment:{appointment_id}"
    if settings.ENABLE_CACHING:
        cached_appointment = await get_cache(cache_key)
        if cached_appointment:
            return Appointment.model_validate(cached_appointment)
    
    # Get from database
    db_appointment = await get_appointment(db, appointment_id)
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Cache the result
    if settings.ENABLE_CACHING:
        appointment_dict = Appointment.model_validate(db_appointment).model_dump()
        await set_cache(cache_key, appointment_dict, ttl=settings.CACHE_TTL)
    
    return db_appointment


@router.get("/", response_model=List[Appointment])
@limiter.limit("200/hour")
async def list_appointments(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[AppointmentStatus] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List appointments with filters and caching."""
    # Generate cache key from query parameters
    cache_key = f"appointment:list:{skip}:{limit}:{status}:{date_from}:{date_to}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_appointments = await get_cache(cache_key)
        if cached_appointments:
            return [Appointment.model_validate(a) for a in cached_appointments]
    
    # Get from database
    appointments = await get_appointments(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        date_from=date_from,
        date_to=date_to
    )
    
    # Cache the result (shorter TTL for lists)
    if settings.ENABLE_CACHING:
        appointments_dict = [Appointment.model_validate(a).model_dump() for a in appointments]
        await set_cache(cache_key, appointments_dict, ttl=300)  # 5 minutes for lists
    
    return appointments


@router.get("/patient/{patient_id}", response_model=List[Appointment])
@limiter.limit("200/hour")
async def get_patient_appointments(
    request: Request,
    patient_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get appointments for a specific patient with caching."""
    cache_key = f"appointment:patient:{patient_id}:{skip}:{limit}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_appointments = await get_cache(cache_key)
        if cached_appointments:
            return [Appointment.model_validate(a) for a in cached_appointments]
    
    # Get from database
    appointments = await get_appointments_by_patient(
        db=db,
        patient_id=patient_id,
        skip=skip,
        limit=limit
    )
    
    # Cache the result
    if settings.ENABLE_CACHING:
        appointments_dict = [Appointment.model_validate(a).model_dump() for a in appointments]
        await set_cache(cache_key, appointments_dict, ttl=600)  # 10 minutes
    
    return appointments


@router.get("/doctor/{doctor_id}", response_model=List[Appointment])
@limiter.limit("200/hour")
async def get_doctor_appointments(
    request: Request,
    doctor_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get appointments for a specific doctor with caching."""
    cache_key = f"appointment:doctor:{doctor_id}:{skip}:{limit}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_appointments = await get_cache(cache_key)
        if cached_appointments:
            return [Appointment.model_validate(a) for a in cached_appointments]
    
    # Get from database
    appointments = await get_appointments_by_doctor(
        db=db,
        doctor_id=doctor_id,
        skip=skip,
        limit=limit
    )
    
    # Cache the result
    if settings.ENABLE_CACHING:
        appointments_dict = [Appointment.model_validate(a).model_dump() for a in appointments]
        await set_cache(cache_key, appointments_dict, ttl=300)  # 5 minutes (doctor schedules change frequently)
    
    return appointments


@router.get("/upcoming/list", response_model=List[Appointment])
@limiter.limit("200/hour")
async def get_upcoming_appointments_endpoint(
    request: Request,
    patient_id: Optional[str] = Query(None),
    doctor_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming appointments with caching."""
    cache_key = f"appointment:upcoming:{patient_id or 'all'}:{doctor_id or 'all'}:{limit}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_appointments = await get_cache(cache_key)
        if cached_appointments:
            return [Appointment.model_validate(a) for a in cached_appointments]
    
    # Get from database
    appointments = await get_upcoming_appointments(
        db=db,
        patient_id=patient_id,
        doctor_id=doctor_id,
        limit=limit
    )
    
    # Cache for 5 minutes (upcoming appointments change frequently)
    if settings.ENABLE_CACHING:
        appointments_dict = [Appointment.model_validate(a).model_dump() for a in appointments]
        await set_cache(cache_key, appointments_dict, ttl=300)
    
    return appointments


@router.put("/{appointment_id}", response_model=Appointment)
@limiter.limit("100/hour")
async def update_appointment_endpoint(
    appointment_id: str,
    appointment_update: AppointmentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update appointment information with caching and retry."""
    try:
        # If appointment date/time is being updated, check availability
        if appointment_update.appointment_date or appointment_update.appointment_time:
            existing_appointment = await get_appointment(db, appointment_id)
            if existing_appointment:
                new_date = appointment_update.appointment_date or existing_appointment.appointment_date
                new_duration = appointment_update.duration_minutes or existing_appointment.duration_minutes
                doctor_id = appointment_update.doctor_id or existing_appointment.doctor_id
                
                # Check cache for availability
                availability_cache_key = f"appointment:availability:{doctor_id}:{new_date.isoformat()}"
                cached_availability = await get_cache(availability_cache_key)
                
                if cached_availability is not None:
                    is_available = cached_availability
                else:
                    # Check with retry
                    retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
                    is_available = await retry_with_backoff(
                        check_doctor_availability,
                        db=db,
                        doctor_id=doctor_id,
                        appointment_date=new_date,
                        duration_minutes=new_duration,
                        exclude_appointment_id=appointment_id,
                        config=retry_config
                    )
                    await set_cache(availability_cache_key, is_available, ttl=300)
                
                if not is_available:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Doctor is not available at the requested time"
                    )
        
        # Update with retry
        retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
        updated_by = current_user.get("email") or current_user.get("user_id")
        db_appointment = await retry_with_backoff(
            update_appointment,
            db=db,
            appointment_id=appointment_id,
            appointment_update=appointment_update,
            updated_by=updated_by,
            config=retry_config
        )
        
        if not db_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Invalidate cache
        background_tasks.add_task(
            invalidate_appointment_cache,
            appointment_id=appointment_id,
            patient_id=db_appointment.patient_id,
            doctor_id=db_appointment.doctor_id
        )
        
        return db_appointment
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment conflict detected"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{appointment_id}/cancel", response_model=Appointment)
@limiter.limit("10/hour")
async def cancel_appointment_endpoint(
    appointment_id: str,
    cancel_data: AppointmentCancel,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an appointment with caching and notifications."""
    cancelled_by = current_user.get("email") or current_user.get("user_id")
    
    # Cancel with retry
    retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
    db_appointment = await retry_with_backoff(
        cancel_appointment,
        db=db,
        appointment_id=appointment_id,
        cancellation_reason=cancel_data.cancellation_reason,
        cancelled_by=cancelled_by or cancel_data.cancelled_by,
        config=retry_config
    )
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Invalidate cache
    background_tasks.add_task(
        invalidate_appointment_cache,
        appointment_id=appointment_id,
        patient_id=db_appointment.patient_id,
        doctor_id=db_appointment.doctor_id
    )
    
    # Send notification
    background_tasks.add_task(
        send_appointment_notification,
        appointment_id=appointment_id,
        notification_type="cancelled",
        data={"appointment": appointment_id, "reason": cancel_data.cancellation_reason}
    )
    
    active_appointments_gauge.dec()
    return db_appointment


@router.post("/{appointment_id}/reschedule", response_model=Appointment)
@limiter.limit("10/hour")
async def reschedule_appointment_endpoint(
    appointment_id: str,
    reschedule_data: AppointmentReschedule,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reschedule an appointment with caching and retry."""
    # Get existing appointment (with cache)
    cache_key = f"appointment:{appointment_id}"
    if settings.ENABLE_CACHING:
        cached_appointment = await get_cache(cache_key)
        if cached_appointment:
            existing_appointment = Appointment.model_validate(cached_appointment)
        else:
            existing_appointment = await get_appointment(db, appointment_id)
    else:
        existing_appointment = await get_appointment(db, appointment_id)
    
    if not existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check doctor availability at new time (with cache)
    availability_cache_key = f"appointment:availability:{existing_appointment.doctor_id}:{reschedule_data.new_appointment_date.isoformat()}"
    cached_availability = await get_cache(availability_cache_key)
    
    if cached_availability is not None:
        is_available = cached_availability
    else:
        retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
        is_available = await retry_with_backoff(
            check_doctor_availability,
            db=db,
            doctor_id=existing_appointment.doctor_id,
            appointment_date=reschedule_data.new_appointment_date,
            duration_minutes=existing_appointment.duration_minutes,
            exclude_appointment_id=appointment_id,
            config=retry_config
        )
        await set_cache(availability_cache_key, is_available, ttl=300)
    
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor is not available at the requested time"
        )
    
    # Update appointment
    appointment_update = AppointmentUpdate(
        appointment_date=reschedule_data.new_appointment_date,
        appointment_time=reschedule_data.new_appointment_time,
        notes=reschedule_data.reason
    )
    appointment_update.status = AppointmentStatus.RESCHEDULED
    
    updated_by = current_user.get("email") or current_user.get("user_id")
    retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
    db_appointment = await retry_with_backoff(
        update_appointment,
        db=db,
        appointment_id=appointment_id,
        appointment_update=appointment_update,
        updated_by=updated_by,
        config=retry_config
    )
    
    # Invalidate cache
    background_tasks.add_task(
        invalidate_appointment_cache,
        appointment_id=appointment_id,
        patient_id=db_appointment.patient_id,
        doctor_id=db_appointment.doctor_id
    )
    
    # Send notification
    background_tasks.add_task(
        send_appointment_notification,
        appointment_id=appointment_id,
        notification_type="rescheduled",
        data={"appointment": appointment_id, "new_date": reschedule_data.new_appointment_date.isoformat()}
    )
    
    return db_appointment


@router.get("/availability/check", response_model=dict)
@limiter.limit("200/hour")
async def check_availability(
    request: Request,
    doctor_id: str = Query(..., description="Doctor ID"),
    appointment_date: datetime = Query(..., description="Proposed appointment date and time"),
    duration_minutes: int = Query(30, ge=15, le=240, description="Appointment duration in minutes"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if doctor is available at the specified time with caching."""
    # Check cache first
    cache_key = f"appointment:availability:{doctor_id}:{appointment_date.isoformat()}:{duration_minutes}"
    
    if settings.ENABLE_CACHING:
        cached_result = await get_cache(cache_key)
        if cached_result is not None:
            return cached_result
    
    # Check availability with retry
    retry_config = RetryConfig(max_attempts=3, initial_delay=0.5)
    is_available = await retry_with_backoff(
        check_doctor_availability,
        db=db,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        duration_minutes=duration_minutes,
        config=retry_config
    )
    
    result = {
        "available": is_available,
        "doctor_id": doctor_id,
        "appointment_date": appointment_date.isoformat(),
        "duration_minutes": duration_minutes,
        "cached": False
    }
    
    # Cache the result (short TTL for availability)
    if settings.ENABLE_CACHING:
        await set_cache(cache_key, result, ttl=300)  # 5 minutes
    else:
        result["cached"] = False
    
    return result


@router.get("/stats/summary", response_model=dict)
@limiter.limit("100/hour")
async def get_appointment_stats(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get appointment statistics with caching."""
    cache_key = "appointment:stats:summary"
    
    # Try cache first (stats change less frequently)
    if settings.ENABLE_CACHING:
        cached_stats = await get_cache(cache_key)
        if cached_stats:
            cached_stats["cached"] = True
            return cached_stats
    
    # Get from database
    pending_count = await count_appointments_by_status(db, AppointmentStatus.PENDING)
    confirmed_count = await count_appointments_by_status(db, AppointmentStatus.CONFIRMED)
    cancelled_count = await count_appointments_by_status(db, AppointmentStatus.CANCELLED)
    completed_count = await count_appointments_by_status(db, AppointmentStatus.COMPLETED)
    
    stats = {
        "pending": pending_count,
        "confirmed": confirmed_count,
        "cancelled": cancelled_count,
        "completed": completed_count,
        "total": pending_count + confirmed_count + cancelled_count + completed_count,
        "cached": False
    }
    
    # Cache stats for 10 minutes
    if settings.ENABLE_CACHING:
        await set_cache(cache_key, stats, ttl=600)
    
    return stats


@router.get("/health/check", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint with database connectivity."""
    try:
        await count_appointments_by_status(db, AppointmentStatus.PENDING)
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthCheck(
        status="healthy" if db_status == "connected" else "unhealthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        database=db_status
    )

