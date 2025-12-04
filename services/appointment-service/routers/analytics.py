"""Analytics and reporting endpoints."""
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter
# Metrics defined in main.py

from database import get_db
from models import Appointment, AppointmentStatus
from dependencies import get_current_user
from rate_limit import limiter
from config import Settings
settings = Settings()
from cache import get_cache, set_cache

router = APIRouter(prefix="/api/v1/appointments", tags=["analytics"])



@router.get("/analytics/daily", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("100/hour")
async def get_daily_analytics(
    request: Request,
    date: Optional[datetime] = Query(None, description="Date for analytics (default: today)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily appointment analytics."""
    if not date:
        date = datetime.utcnow().date()
    
    cache_key = f"appointment:analytics:daily:{date.isoformat()}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_analytics = await get_cache(cache_key)
        if cached_analytics:
            request_count.labels(endpoint='daily', status='200').inc()
            return cached_analytics
    
    # Calculate date range
    start_date = datetime.combine(date, datetime.min.time())
    end_date = start_date + timedelta(days=1)
    
    # Get statistics
    total_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date < end_date,
                Appointment.is_active == True
            )
        )
    )
    total = total_result.scalar() or 0
    
    # Get by status
    status_counts = {}
    for status in AppointmentStatus:
        count_result = await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.appointment_date >= start_date,
                    Appointment.appointment_date < end_date,
                    Appointment.status == status,
                    Appointment.is_active == True
                )
            )
        )
        status_counts[status.value] = count_result.scalar() or 0
    
    analytics = {
        "date": date.isoformat(),
        "total": total,
        "by_status": status_counts,
        "cached": False
    }
    
    # Cache for 10 minutes
    if settings.ENABLE_CACHING:
        await set_cache(cache_key, analytics, ttl=600)
    
    request_count.labels(endpoint='daily', status='200').inc()
    return analytics


@router.get("/analytics/doctor/{doctor_id}", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("100/hour")
async def get_doctor_analytics(
    request: Request,
    doctor_id: str,
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get doctor appointment analytics."""
    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()
    
    cache_key = f"appointment:analytics:doctor:{doctor_id}:{date_from.isoformat()}:{date_to.isoformat()}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_analytics = await get_cache(cache_key)
        if cached_analytics:
            request_count.labels(endpoint='doctor', status='200').inc()
            return cached_analytics
    
    # Get statistics
    total_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date >= date_from,
                Appointment.appointment_date <= date_to,
                Appointment.is_active == True
            )
        )
    )
    total = total_result.scalar() or 0
    
    # Get by status
    status_counts = {}
    for status in AppointmentStatus:
        count_result = await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date >= date_from,
                    Appointment.appointment_date <= date_to,
                    Appointment.status == status,
                    Appointment.is_active == True
                )
            )
        )
        status_counts[status.value] = count_result.scalar() or 0
    
    analytics = {
        "doctor_id": doctor_id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": total,
        "by_status": status_counts,
        "cached": False
    }
    
    # Cache for 15 minutes
    if settings.ENABLE_CACHING:
        await set_cache(cache_key, analytics, ttl=900)
    
    request_count.labels(endpoint='doctor', status='200').inc()
    return analytics


@router.get("/analytics/patient/{patient_id}", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("100/hour")
async def get_patient_analytics(
    request: Request,
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get patient appointment analytics."""
    cache_key = f"appointment:analytics:patient:{patient_id}"
    
    # Try cache first
    if settings.ENABLE_CACHING:
        cached_analytics = await get_cache(cache_key)
        if cached_analytics:
            request_count.labels(endpoint='patient', status='200').inc()
            return cached_analytics
    
    # Get statistics
    total_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.is_active == True
            )
        )
    )
    total = total_result.scalar() or 0
    
    # Get by status
    status_counts = {}
    for status in AppointmentStatus:
        count_result = await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == status,
                    Appointment.is_active == True
                )
            )
        )
        status_counts[status.value] = count_result.scalar() or 0
    
    # Get upcoming count
    upcoming_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.appointment_date >= datetime.utcnow(),
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                Appointment.is_active == True
            )
        )
    )
    upcoming = upcoming_result.scalar() or 0
    
    analytics = {
        "patient_id": patient_id,
        "total": total,
        "upcoming": upcoming,
        "by_status": status_counts,
        "cached": False
    }
    
    # Cache for 10 minutes
    if settings.ENABLE_CACHING:
        await set_cache(cache_key, analytics, ttl=600)
    
    request_count.labels(endpoint='patient', status='200').inc()
    return analytics

