"""Database CRUD operations for appointments."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from models import Appointment, DoctorAvailability, AppointmentStatus, AppointmentPriority
from schemas import AppointmentCreate, AppointmentUpdate


def generate_appointment_id() -> str:
    """Generate unique appointment ID in format APT-XXXXX."""
    unique_id = str(uuid.uuid4()).replace("-", "").upper()[:8]
    return f"APT-{unique_id}"


async def create_appointment(db: AsyncSession, appointment: AppointmentCreate, created_by: Optional[str] = None) -> Appointment:
    """
    Create a new appointment record.
    
    Args:
        db: Database session
        appointment: Appointment creation data
        created_by: User who created the appointment
        
    Returns:
        Appointment: Created appointment object
        
    Raises:
        IntegrityError: If appointment conflicts with existing appointment
    """
    appointment_data = appointment.model_dump()
    appointment_data["appointment_id"] = generate_appointment_id()
    appointment_data["created_by"] = created_by
    
    # Calculate end time
    appointment_date = appointment_data["appointment_date"]
    duration = appointment_data.get("duration_minutes", 30)
    appointment_data["end_time"] = appointment_date + timedelta(minutes=duration)
    
    db_appointment = Appointment(**appointment_data)
    db.add(db_appointment)
    try:
        await db.commit()
        await db.refresh(db_appointment)
        return db_appointment
    except IntegrityError as e:
        await db.rollback()
        raise e


async def get_appointment(db: AsyncSession, appointment_id: str) -> Optional[Appointment]:
    """
    Get appointment by appointment_id.
    
    Args:
        db: Database session
        appointment_id: Appointment ID (format: APT-XXXXX)
        
    Returns:
        Appointment or None if not found
    """
    result = await db.execute(
        select(Appointment).where(
            Appointment.appointment_id == appointment_id,
            Appointment.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def get_appointments_by_patient(
    db: AsyncSession,
    patient_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Appointment]:
    """
    Get appointments for a specific patient.
    
    Args:
        db: Database session
        patient_id: Patient ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Appointment objects
    """
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.is_active == True
        )
        .offset(skip)
        .limit(limit)
        .order_by(Appointment.appointment_date.desc())
    )
    return list(result.scalars().all())


async def get_appointments_by_doctor(
    db: AsyncSession,
    doctor_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Appointment]:
    """
    Get appointments for a specific doctor.
    
    Args:
        db: Database session
        doctor_id: Doctor ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Appointment objects
    """
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.doctor_id == doctor_id,
            Appointment.is_active == True
        )
        .offset(skip)
        .limit(limit)
        .order_by(Appointment.appointment_date.desc())
    )
    return list(result.scalars().all())


async def get_appointments(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Appointment]:
    """
    Get list of appointments with filters.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        date_from: Filter by date from
        date_to: Filter by date to
        
    Returns:
        List of Appointment objects
    """
    conditions = [Appointment.is_active == True]
    
    if status:
        conditions.append(Appointment.status == status)
    
    if date_from:
        conditions.append(Appointment.appointment_date >= date_from)
    
    if date_to:
        conditions.append(Appointment.appointment_date <= date_to)
    
    result = await db.execute(
        select(Appointment)
        .where(and_(*conditions))
        .offset(skip)
        .limit(limit)
        .order_by(Appointment.appointment_date.desc())
    )
    return list(result.scalars().all())


async def update_appointment(
    db: AsyncSession,
    appointment_id: str,
    appointment_update: AppointmentUpdate,
    updated_by: Optional[str] = None
) -> Optional[Appointment]:
    """
    Update appointment information.
    
    Args:
        db: Database session
        appointment_id: Appointment ID to update
        appointment_update: Appointment update data
        updated_by: User who updated the appointment
        
    Returns:
        Updated Appointment or None if not found
    """
    db_appointment = await get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    update_data = appointment_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_appointment
    
    # Update end_time if appointment_date or duration_minutes changed
    if "appointment_date" in update_data or "duration_minutes" in update_data:
        appointment_date = update_data.get("appointment_date", db_appointment.appointment_date)
        duration = update_data.get("duration_minutes", db_appointment.duration_minutes)
        update_data["end_time"] = appointment_date + timedelta(minutes=duration)
    
    # Update fields
    for field, value in update_data.items():
        setattr(db_appointment, field, value)
    
    db_appointment.updated_by = updated_by
    db_appointment.updated_at = datetime.utcnow()
    
    try:
        await db.commit()
        await db.refresh(db_appointment)
        return db_appointment
    except IntegrityError as e:
        await db.rollback()
        raise e


async def cancel_appointment(
    db: AsyncSession,
    appointment_id: str,
    cancellation_reason: Optional[str] = None,
    cancelled_by: Optional[str] = None
) -> Optional[Appointment]:
    """
    Cancel an appointment.
    
    Args:
        db: Database session
        appointment_id: Appointment ID to cancel
        cancellation_reason: Reason for cancellation
        cancelled_by: User who cancelled
        
    Returns:
        Cancelled Appointment or None if not found
    """
    db_appointment = await get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    db_appointment.status = AppointmentStatus.CANCELLED
    db_appointment.cancelled_at = datetime.utcnow()
    db_appointment.cancellation_reason = cancellation_reason
    db_appointment.cancelled_by = cancelled_by
    db_appointment.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_appointment)
    return db_appointment


async def check_doctor_availability(
    db: AsyncSession,
    doctor_id: str,
    appointment_date: datetime,
    duration_minutes: int = 30,
    exclude_appointment_id: Optional[str] = None
) -> bool:
    """
    Check if doctor is available at the specified time.
    
    Args:
        db: Database session
        doctor_id: Doctor ID
        appointment_date: Proposed appointment date and time
        duration_minutes: Appointment duration in minutes
        exclude_appointment_id: Appointment ID to exclude from conflict check
        
    Returns:
        True if available, False if conflict exists
    """
    end_time = appointment_date + timedelta(minutes=duration_minutes)
    
    # Check for conflicting appointments
    conditions = [
        Appointment.doctor_id == doctor_id,
        Appointment.is_active == True,
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
        or_(
            and_(
                Appointment.appointment_date <= appointment_date,
                Appointment.end_time > appointment_date
            ),
            and_(
                Appointment.appointment_date < end_time,
                Appointment.end_time >= end_time
            ),
            and_(
                Appointment.appointment_date >= appointment_date,
                Appointment.end_time <= end_time
            )
        )
    ]
    
    if exclude_appointment_id:
        conditions.append(Appointment.appointment_id != exclude_appointment_id)
    
    result = await db.execute(
        select(func.count(Appointment.id)).where(and_(*conditions))
    )
    conflict_count = result.scalar() or 0
    
    return conflict_count == 0


async def get_upcoming_appointments(
    db: AsyncSession,
    patient_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    limit: int = 10
) -> List[Appointment]:
    """
    Get upcoming appointments.
    
    Args:
        db: Database session
        patient_id: Optional patient ID filter
        doctor_id: Optional doctor ID filter
        limit: Maximum number of records
        
    Returns:
        List of upcoming Appointment objects
    """
    conditions = [
        Appointment.is_active == True,
        Appointment.appointment_date >= datetime.utcnow(),
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
    ]
    
    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)
    
    if doctor_id:
        conditions.append(Appointment.doctor_id == doctor_id)
    
    result = await db.execute(
        select(Appointment)
        .where(and_(*conditions))
        .order_by(Appointment.appointment_date.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_appointments_by_status(db: AsyncSession, status: AppointmentStatus) -> int:
    """
    Count appointments by status.
    
    Args:
        db: Database session
        status: Appointment status
        
    Returns:
        Number of appointments with the status
    """
    result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.status == status,
            Appointment.is_active == True
        )
    )
    return result.scalar() or 0

