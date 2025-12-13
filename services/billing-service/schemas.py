"""
Pydantic Schemas for Billing Service.

This module defines request/response schemas for invoices, payments, and claims.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from common.models.shared_types import Money


class InvoiceStatusEnum(str, Enum):
    """FHIR Invoice Status codes."""

    DRAFT = "draft"
    ISSUED = "issued"
    BALANCED = "balanced"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered-in-error"


class PaymentStatusEnum(str, Enum):
    """Payment Status codes."""

    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ClaimStatusEnum(str, Enum):
    """FHIR Claim Status codes."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    ENTERED_IN_ERROR = "entered-in-error"


# Invoice Schemas


class InvoiceLineItemCreate(BaseModel):
    """Schema for creating invoice line item."""

    sequence: int = Field(..., description="Item sequence number", ge=1)
    code: str = Field(
        ..., description="Service/product code (CPT, HCPCS)", min_length=1
    )
    description: Optional[str] = Field(None, description="Item description")
    quantity: Decimal = Field(default=Decimal("1.0"), description="Item quantity", ge=0)
    unit_price: Money = Field(..., description="Unit price")
    line_total: Money = Field(..., description="Line item total")

    @model_validator(mode="after")
    def validate_line_total(self) -> "InvoiceLineItemCreate":
        """Validate line total matches quantity * unit_price."""
        if self.quantity and self.unit_price and self.line_total:
            from decimal import Decimal

            expected_total = Decimal(str(self.quantity)) * Decimal(
                str(self.unit_price.value)
            )
            actual_total = Decimal(str(self.line_total.value))
            if abs(actual_total - expected_total) > Decimal("0.01"):
                raise ValueError("Line total must equal quantity * unit_price")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "sequence": 1,
                "code": "99213",
                "description": "Office visit - established patient",
                "quantity": 1,
                "unit_price": {"value": 150.00, "currency": "USD"},
                "line_total": {"value": 150.00, "currency": "USD"},
            }
        }


class InvoiceLineItemResponse(BaseModel):
    """Schema for invoice line item response."""

    id: str
    sequence: int
    code: str
    description: Optional[str]
    quantity: Decimal
    unit_price: Money
    line_total: Money
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, "hex"):
            return str(v)
        return v

    @field_validator("unit_price", "line_total", mode="before")
    @classmethod
    def convert_decimal_to_money(cls, v):
        """Convert Decimal to Money object."""
        if isinstance(v, Decimal):
            return Money(value=v, currency="USD")
        return v

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    """Schema for creating invoice."""

    subject: str = Field(..., description="Patient ID", min_length=1)
    date: datetime = Field(..., description="Invoice date")
    line_items: List[InvoiceLineItemCreate] = Field(
        ..., description="Line items", min_length=1
    )
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    appointment_id: Optional[str] = Field(None, description="Associated appointment ID")
    account_id: Optional[str] = Field(None, description="Billing account ID")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: datetime) -> datetime:
        """Ensure date is not in future."""
        if v > datetime.now(timezone.utc):
            raise ValueError("Invoice date cannot be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "pat-123",
                "date": "2025-12-01T10:00:00Z",
                "line_items": [
                    {
                        "sequence": 1,
                        "code": "99213",
                        "description": "Office visit",
                        "quantity": 1,
                        "unit_price": {"value": 150.00, "currency": "USD"},
                        "line_total": {"value": 150.00, "currency": "USD"},
                    }
                ],
                "payment_terms": "Net 30",
                "appointment_id": "apt-456",
            }
        }


class InvoiceUpdate(BaseModel):
    """Schema for updating invoice."""

    status: Optional[InvoiceStatusEnum] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"status": "issued", "payment_terms": "Net 30"}}


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""

    id: str
    resource_type: str = "Invoice"
    status: InvoiceStatusEnum
    subject: str
    date: datetime
    line_items: List[InvoiceLineItemResponse]
    total_net_amount: Optional[Decimal]
    total_gross_amount: Optional[Decimal]
    total_paid_amount: Decimal
    total_due_amount: Optional[Decimal]
    currency: str
    payment_terms: Optional[str]
    notes: Optional[str]
    appointment_id: Optional[str]
    account_id: Optional[str]
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, "hex"):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "inv-123e4567-e89b-12d3-a456-426614174000",
                "resource_type": "Invoice",
                "status": "issued",
                "subject": "pat-123",
                "date": "2025-12-01T10:00:00Z",
                "line_items": [
                    {
                        "id": "item-123",
                        "sequence": 1,
                        "code": "99213",
                        "description": "Office visit",
                        "quantity": 1,
                        "unit_price": {"value": 150.00, "currency": "USD"},
                        "line_total": {"value": 150.00, "currency": "USD"},
                        "created_at": "2025-12-01T10:00:00Z",
                    }
                ],
                "total_due_amount": 150.00,
                "total_paid_amount": 0.00,
                "currency": "USD",
                "created_at": "2025-12-01T10:00:00Z",
                "updated_at": "2025-12-01T10:00:00Z",
            }
        }


# Payment Schemas


class PaymentRecordCreate(BaseModel):
    """Schema for creating payment record."""

    invoice_id: str = Field(..., description="Invoice ID")
    amount: Money = Field(..., description="Payment amount")
    payment_method: str = Field(
        ..., description="Payment method (cash, card, check, wire, insurance)"
    )
    payment_date: datetime = Field(..., description="Payment date")
    reference_number: Optional[str] = Field(
        None, description="Transaction reference number"
    )
    notes: Optional[str] = Field(None, description="Payment notes")

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: datetime) -> datetime:
        """Ensure payment date is not in future."""
        if v > datetime.now(timezone.utc):
            raise ValueError("Payment date cannot be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "inv-123e4567-e89b-12d3-a456-426614174000",
                "amount": {"value": 150.00, "currency": "USD"},
                "payment_method": "card",
                "payment_date": "2025-12-01T10:00:00Z",
                "reference_number": "TXN-12345",
            }
        }


class PaymentRecordUpdate(BaseModel):
    """Schema for updating payment record."""

    payment_status: Optional[PaymentStatusEnum] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"payment_status": "paid"}}


class PaymentRecordResponse(BaseModel):
    """Schema for payment record response."""

    id: str
    invoice_id: str
    amount: Money
    currency: str
    payment_method: str
    payment_date: datetime
    payment_status: PaymentStatusEnum
    reference_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "invoice_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, "hex"):
            return str(v)
        return v

    @field_validator("amount", mode="before")
    @classmethod
    def convert_decimal_to_money(cls, v):
        """Convert Decimal to Money object."""
        if isinstance(v, Decimal):
            return Money(value=v, currency="USD")
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "pay-123e4567-e89b-12d3-a456-426614174000",
                "invoice_id": "inv-123e4567-e89b-12d3-a456-426614174000",
                "amount": {"value": 150.00, "currency": "USD"},
                "currency": "USD",
                "payment_method": "card",
                "payment_date": "2025-12-01T10:00:00Z",
                "payment_status": "paid",
                "reference_number": "TXN-12345",
                "created_at": "2025-12-01T10:00:00Z",
                "updated_at": "2025-12-01T10:00:00Z",
            }
        }


# Insurance Claim Schemas


class ClaimItemCreate(BaseModel):
    """Schema for claim item."""

    sequence: int = Field(..., description="Item sequence number", ge=1)
    code: str = Field(..., description="Service/product code", min_length=1)
    description: Optional[str] = Field(None, description="Item description")
    quantity: Optional[Decimal] = Field(Decimal("1.0"), description="Quantity", ge=0)
    unit_price: Money = Field(..., description="Unit price")
    net_amount: Money = Field(..., description="Net amount")

    class Config:
        json_schema_extra = {
            "example": {
                "sequence": 1,
                "code": "99213",
                "description": "Office visit",
                "quantity": 1,
                "unit_price": {"value": 150.00, "currency": "USD"},
                "net_amount": {"value": 150.00, "currency": "USD"},
            }
        }


class InsuranceClaimCreate(BaseModel):
    """Schema for creating insurance claim."""

    claim_number: str = Field(..., description="Unique claim number", min_length=1)
    type: str = Field(
        ..., description="Claim type (institutional, professional, pharmacy)"
    )
    patient_id: str = Field(..., description="Patient ID", min_length=1)
    provider_id: Optional[str] = Field(None, description="Provider ID")
    insurer_name: str = Field(..., description="Insurance company name", min_length=1)
    policy_number: str = Field(..., description="Policy number", min_length=1)
    created_date: datetime = Field(..., description="Claim creation date")
    billable_period_start: date = Field(..., description="Billable period start date")
    billable_period_end: date = Field(..., description="Billable period end date")
    items: List[ClaimItemCreate] = Field(..., description="Claim line items")

    @model_validator(mode="after")
    def validate_billable_period(self) -> "InsuranceClaimCreate":
        """Ensure billable period end is after start."""
        if self.billable_period_end < self.billable_period_start:
            raise ValueError("Billable period end must be after start")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "claim_number": "CLM-2025-001",
                "type": "professional",
                "patient_id": "pat-123",
                "provider_id": "prov-456",
                "insurer_name": "Blue Cross Blue Shield",
                "policy_number": "POL-789",
                "created_date": "2025-12-01T10:00:00Z",
                "items": [
                    {
                        "sequence": 1,
                        "code": "99213",
                        "description": "Office visit",
                        "quantity": 1,
                        "unit_price": {"value": 150.00, "currency": "USD"},
                        "net_amount": {"value": 150.00, "currency": "USD"},
                    }
                ],
            }
        }


class InsuranceClaimUpdate(BaseModel):
    """Schema for updating insurance claim."""

    status: Optional[ClaimStatusEnum] = None

    class Config:
        json_schema_extra = {"example": {"status": "active"}}


class InsuranceClaimResponse(BaseModel):
    """Schema for insurance claim response."""

    id: str
    resource_type: str = "Claim"
    claim_number: str
    status: ClaimStatusEnum
    type: str
    patient_id: str
    provider_id: Optional[str]
    insurer_name: str
    policy_number: str
    created_date: datetime
    billable_period_start: Optional[datetime]
    billable_period_end: Optional[datetime]
    total_amount: Optional[Decimal]
    currency: str
    claim_items: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, "hex"):
            return str(v)
        return v

    class Config:
        from_attributes = True


# List and Pagination Schemas


class InvoiceListResponse(BaseModel):
    """Schema for list of invoices."""

    total: int
    count: int
    items: List[InvoiceResponse]


class PaymentListResponse(BaseModel):
    """Schema for list of payments."""

    total: int
    count: int
    items: List[PaymentRecordResponse]


class ClaimListResponse(BaseModel):
    """Schema for list of claims."""

    total: int
    count: int
    items: List[InsuranceClaimResponse]


# Report Schemas


class RevenueReportResponse(BaseModel):
    """Schema for revenue report."""

    period_start: datetime
    period_end: datetime
    total_invoices: int
    total_revenue: Money
    total_paid: Money
    total_outstanding: Money
    by_status: Dict[str, Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "period_start": "2025-11-01T00:00:00Z",
                "period_end": "2025-11-30T23:59:59Z",
                "total_invoices": 25,
                "total_revenue": {"value": 3750.00, "currency": "USD"},
                "total_paid": {"value": 3000.00, "currency": "USD"},
                "total_outstanding": {"value": 750.00, "currency": "USD"},
                "by_status": {
                    "issued": {
                        "count": 15,
                        "amount": {"value": 2250.00, "currency": "USD"},
                    },
                    "balanced": {
                        "count": 10,
                        "amount": {"value": 1500.00, "currency": "USD"},
                    },
                },
            }
        }


class PatientBillingSummaryResponse(BaseModel):
    """Schema for patient billing summary."""

    patient_id: str
    total_invoices: int
    total_billed: Money
    total_paid: Money
    total_outstanding: Money
    recent_invoices: List[InvoiceResponse]
    recent_payments: List[PaymentRecordResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "pat-123",
                "total_invoices": 5,
                "total_billed": {"value": 750.00, "currency": "USD"},
                "total_paid": {"value": 500.00, "currency": "USD"},
                "total_outstanding": {"value": 250.00, "currency": "USD"},
                "recent_invoices": [],
                "recent_payments": [],
            }
        }


# Health Check Schema


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    service: str
    status: str
    database: str
    rabbitmq: Optional[str]
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "service": "billing-service",
                "status": "healthy",
                "database": "connected",
                "rabbitmq": "connected",
                "timestamp": "2025-12-01T10:00:00Z",
            }
        }


class PaymentRecordListResponse(BaseModel):
    """Schema for payment record list response."""

    payments: List[PaymentRecordResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "payments": [],
                "total": 0,
            }
        }


class InsuranceClaimListResponse(BaseModel):
    """Schema for insurance claim list response."""

    claims: List[InsuranceClaimResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "claims": [],
                "total": 0,
            }
        }
