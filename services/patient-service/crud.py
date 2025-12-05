"""Database CRUD operations for patients."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime
import uuid

from models import Patient
from schemas import PatientCreate, PatientUpdate


def generate_patient_id() -> str:
    """Generate unique patient ID in format PAT-XXXXX."""
    unique_id = str(uuid.uuid4()).replace("-", "").upper()[:8]
    return f"PAT-{unique_id}"


async def create_patient(db: AsyncSession, patient: PatientCreate) -> Patient:
    """
    Create a new patient record.
    
    Args:
        db: Database session
        patient: Patient creation data
        
    Returns:
        Patient: Created patient object
        
    Raises:
        IntegrityError: If email already exists
    """
    patient_data = patient.model_dump()
    patient_data["patient_id"] = generate_patient_id()
    db_patient = Patient(**patient_data)
    db.add(db_patient)
    try:
        await db.commit()
        await db.refresh(db_patient)
        return db_patient
    except IntegrityError as e:
        await db.rollback()
        raise e


async def get_patient(db: AsyncSession, patient_id: str) -> Optional[Patient]:
    """
    Get patient by patient_id.
    
    Args:
        db: Database session
        patient_id: Patient ID (format: PAT-XXXXX)
        
    Returns:
        Patient or None if not found
    """
    result = await db.execute(
        select(Patient).where(
            Patient.patient_id == patient_id,
            Patient.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def get_patient_by_email(db: AsyncSession, email: str) -> Optional[Patient]:
    """
    Get patient by email address.
    
    Args:
        db: Database session
        email: Patient email address
        
    Returns:
        Patient or None if not found
    """
    result = await db.execute(
        select(Patient).where(
            Patient.email == email,
            Patient.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def get_patients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[Patient]:
    """
    Get list of active patients with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Patient objects
    """
    result = await db.execute(
        select(Patient)
        .where(Patient.is_active == True)
        .offset(skip)
        .limit(limit)
        .order_by(Patient.created_at.desc())
    )
    return list(result.scalars().all())


async def update_patient(
    db: AsyncSession,
    patient_id: str,
    patient_update: PatientUpdate
) -> Optional[Patient]:
    """
    Update patient information.
    
    Args:
        db: Database session
        patient_id: Patient ID to update
        patient_update: Patient update data
        
    Returns:
        Updated Patient or None if not found
    """
    # Get existing patient
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        return None
    
    # Update only provided fields
    update_data = patient_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_patient
    
    # Check if email is being updated and if it's already taken
    if 'email' in update_data and update_data['email'] != db_patient.email:
        existing = await get_patient_by_email(db, update_data['email'])
        if existing and existing.patient_id != patient_id:
            raise IntegrityError(
                statement=None,
                params=None,
                orig=Exception("Email already exists")
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(db_patient, field, value)
    
    db_patient.updated_at = datetime.utcnow()
    
    try:
        await db.commit()
        await db.refresh(db_patient)
        return db_patient
    except IntegrityError as e:
        await db.rollback()
        raise e


async def delete_patient(db: AsyncSession, patient_id: str) -> bool:
    """
    Soft delete patient (set is_active=False).
    
    Args:
        db: Database session
        patient_id: Patient ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        return False
    
    db_patient.is_active = False
    db_patient.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_patient)
    return True


async def count_active_patients(db: AsyncSession) -> int:
    """
    Count total number of active patients.
    
    Args:
        db: Database session
        
    Returns:
        Number of active patients
    """
    result = await db.execute(
        select(Patient).where(Patient.is_active == True)
    )
    return len(list(result.scalars().all()))

