"""
Database Models for Billing Service.

This module defines SQLAlchemy ORM models for invoices, payments, and claims.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from database import Base


class Invoice(Base):
    """
    Invoice model (FHIR Invoice compatible).

    Represents a billing invoice for healthcare services.
    """

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String(50), default="Invoice", nullable=False)
    status = Column(String(50), nullable=False)
    subject = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    total_net_amount = Column(Numeric(10, 2))
    total_gross_amount = Column(Numeric(10, 2))
    total_paid_amount = Column(Numeric(10, 2), default=Decimal("0.00"))
    total_due_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")
    payment_terms = Column(Text)
    notes = Column(Text)
    account_id = Column(String(100))
    appointment_id = Column(String(100), index=True)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    line_items = relationship(
        "InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments = relationship(
        "PaymentRecord", back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Invoice."""
        return f"<Invoice(id={self.id}, subject={self.subject}, status={self.status})>"


class InvoiceLineItem(Base):
    """
    Invoice Line Item model.

    Represents individual items/services in an invoice.
    """

    __tablename__ = "invoice_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence = Column(Integer, nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text)
    quantity = Column(Numeric(10, 2))
    unit_price = Column(Numeric(10, 2))
    line_total = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="line_items")

    def __repr__(self) -> str:
        """String representation of InvoiceLineItem."""
        return f"<InvoiceLineItem(id={self.id}, code={self.code}, line_total={self.line_total})>"


class PaymentRecord(Base):
    """
    Payment Record model.

    Represents payments made against invoices.
    """

    __tablename__ = "payment_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(String(50), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_status = Column(String(50), nullable=False)
    reference_number = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self) -> str:
        """String representation of PaymentRecord."""
        return f"<PaymentRecord(id={self.id}, amount={self.amount}, status={self.payment_status})>"


class InsuranceClaim(Base):
    """
    Insurance Claim model (FHIR Claim compatible).

    Represents insurance claims for reimbursement.
    """

    __tablename__ = "insurance_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String(50), default="Claim", nullable=False)
    claim_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    patient_id = Column(String(100), nullable=False, index=True)
    provider_id = Column(String(100))
    insurer_name = Column(String(255))
    policy_number = Column(String(100))
    created_date = Column(DateTime, nullable=False)
    billable_period_start = Column(DateTime)
    billable_period_end = Column(DateTime)
    total_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")
    claim_items = Column(JSONB)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of InsuranceClaim."""
        return f"<InsuranceClaim(id={self.id}, claim_number={self.claim_number}, status={self.status})>"
