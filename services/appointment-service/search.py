"""Advanced search and filtering utilities for appointments."""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from datetime import datetime
from models import Appointment, AppointmentStatus, AppointmentPriority


class AppointmentSearch:
    """Advanced appointment search functionality."""
    
    @staticmethod
    async def search(
        db: AsyncSession,
        query: Optional[str] = None,
        patient_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        doctor_specialization: Optional[str] = None,
        status: Optional[AppointmentStatus] = None,
        priority: Optional[AppointmentPriority] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        location: Optional[str] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "appointment_date",
        sort_order: str = "asc"
    ) -> tuple[List[Appointment], int]:
        """Advanced appointment search with multiple filters."""
        conditions = []
        
        if is_active is not None:
            conditions.append(Appointment.is_active == is_active)
        
        if query:
            search_term = f"%{query.lower()}%"
            conditions.append(
                or_(
                    func.lower(Appointment.patient_name).like(search_term),
                    func.lower(Appointment.doctor_name).like(search_term),
                    Appointment.appointment_id.like(f"%{query}%"),
                    Appointment.patient_id.like(f"%{query}%")
                )
            )
        
        if patient_id:
            conditions.append(Appointment.patient_id == patient_id)
        
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        
        if doctor_name:
            conditions.append(func.lower(Appointment.doctor_name).like(f"%{doctor_name.lower()}%"))
        
        if doctor_specialization:
            conditions.append(func.lower(Appointment.doctor_specialization) == doctor_specialization.lower())
        
        if status:
            conditions.append(Appointment.status == status)
        
        if priority:
            conditions.append(Appointment.priority == priority)
        
        if date_from:
            conditions.append(Appointment.appointment_date >= date_from)
        
        if date_to:
            conditions.append(Appointment.appointment_date <= date_to)
        
        if location:
            conditions.append(func.lower(Appointment.location).like(f"%{location.lower()}%"))
        
        base_query = select(Appointment)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        count_query = select(func.count()).select_from(Appointment)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        sort_column = getattr(Appointment, sort_by, Appointment.appointment_date)
        if sort_order.lower() == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())
        
        base_query = base_query.offset(skip).limit(limit)
        
        result = await db.execute(base_query)
        appointments = list(result.scalars().all())
        
        return appointments, total

