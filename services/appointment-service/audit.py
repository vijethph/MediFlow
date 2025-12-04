"""Audit logging for compliance and tracking."""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base
import json
import logging

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """Audit log model for tracking all appointment data access and modifications."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # Appointment
    resource_id = Column(String(50), nullable=False, index=True)  # appointment_id
    user_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_body = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<AuditLog(event_type={self.event_type}, resource_id={self.resource_id}, created_at={self.created_at})>"


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    resource_type: str,
    resource_id: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    request_body: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log an audit event to the database."""
    try:
        audit_log = AuditLog(
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            request_body=json.dumps(request_body) if request_body else None,
            response_status=response_status,
            correlation_id=correlation_id,
            metadata=metadata
        )
        db.add(audit_log)
        await db.commit()
        logger.info(
            f"Audit: {event_type} {resource_type} {resource_id} by {user_id} "
            f"(IP: {ip_address}, Status: {response_status})"
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        await db.rollback()

