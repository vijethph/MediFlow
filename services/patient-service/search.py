"""Advanced search and filtering utilities."""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from datetime import date, datetime
from models import Patient


class PatientSearch:
    """Advanced patient search functionality."""
    
    @staticmethod
    async def search(
        db: AsyncSession,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        gender: Optional[str] = None,
        blood_group: Optional[str] = None,
        date_of_birth_from: Optional[date] = None,
        date_of_birth_to: Optional[date] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[Patient], int]:
        """
        Advanced patient search with multiple filters.
        
        Args:
            db: Database session
            query: General search query (searches name, email, phone)
            email: Exact email match
            phone: Phone number search
            name: Name search (partial match)
            gender: Gender filter
            blood_group: Blood group filter
            date_of_birth_from: Minimum date of birth
            date_of_birth_to: Maximum date of birth
            is_active: Active status filter
            skip: Number of records to skip
            limit: Maximum number of records
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (patients list, total count)
        """
        # Build base query
        conditions = []
        
        # Active status filter
        if is_active is not None:
            conditions.append(Patient.is_active == is_active)
        
        # General search query
        if query:
            search_term = f"%{query.lower()}%"
            conditions.append(
                or_(
                    func.lower(Patient.full_name).like(search_term),
                    func.lower(Patient.email).like(search_term),
                    Patient.phone.like(f"%{query}%"),
                    Patient.patient_id.like(f"%{query}%")
                )
            )
        
        # Specific filters
        if email:
            conditions.append(func.lower(Patient.email) == email.lower())
        
        if phone:
            conditions.append(Patient.phone.like(f"%{phone}%"))
        
        if name:
            conditions.append(func.lower(Patient.full_name).like(f"%{name.lower()}%"))
        
        if gender:
            conditions.append(func.lower(Patient.gender) == gender.lower())
        
        if blood_group:
            conditions.append(func.upper(Patient.blood_group) == blood_group.upper())
        
        if date_of_birth_from:
            conditions.append(Patient.date_of_birth >= date_of_birth_from)
        
        if date_of_birth_to:
            conditions.append(Patient.date_of_birth <= date_of_birth_to)
        
        # Build query
        base_query = select(Patient)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(Patient)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(Patient, sort_by, Patient.created_at)
        if sort_order.lower() == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())
        
        # Apply pagination
        base_query = base_query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(base_query)
        patients = list(result.scalars().all())
        
        return patients, total
    
    @staticmethod
    async def search_by_filters(
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Patient], int]:
        """
        Search patients using a dictionary of filters.
        
        Args:
            db: Database session
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            Tuple of (patients list, total count)
        """
        return await PatientSearch.search(
            db=db,
            query=filters.get("query"),
            email=filters.get("email"),
            phone=filters.get("phone"),
            name=filters.get("name"),
            gender=filters.get("gender"),
            blood_group=filters.get("blood_group"),
            date_of_birth_from=filters.get("date_of_birth_from"),
            date_of_birth_to=filters.get("date_of_birth_to"),
            is_active=filters.get("is_active", True),
            skip=skip,
            limit=limit,
            sort_by=filters.get("sort_by", "created_at"),
            sort_order=filters.get("sort_order", "desc")
        )

