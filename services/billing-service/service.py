"""
Business Logic Layer for Billing Service.

This module contains all business logic for invoices, payments, and claims.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
import httpx

import models
import schemas
from config import get_settings
from common.exceptions import (
    InvoiceNotFoundError,
    PaymentNotFoundError,
    ClaimNotFoundError,
    ValidationError,
    DuplicateResourceError,
    PatientNotFoundError,
    ServiceUnavailableError,
    InvalidStatusTransitionError,
)
from common.logging import get_logger
from common.messaging import publish_event
from common.utils import retry_on_api_error


settings = get_settings()
logger = get_logger(__name__)


# External Service Integration


@retry_on_api_error(
    max_attempts=3, exceptions=(httpx.RequestError, httpx.HTTPStatusError)
)
async def verify_patient_exists(patient_id: str, jwt_token: str) -> bool:
    """
    Verify patient exists in Patient Service.

    :param patient_id: Patient identifier
    :param jwt_token: JWT authentication token
    :return: True if patient exists
    :raises PatientNotFoundError: If patient not found
    :raises ServiceUnavailableError: If Patient Service unavailable
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.patient_service_url}/api/v1/patients/{patient_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 404:
                raise PatientNotFoundError(patient_id)
            elif response.status_code != 200:
                raise ServiceUnavailableError("Patient Service")

            logger.info("patient_verified", patient_id=patient_id)
            return True
    except httpx.RequestError as e:
        logger.error("patient_service_unavailable", error=str(e))
        raise ServiceUnavailableError("Patient Service") from e


@retry_on_api_error(
    max_attempts=3, exceptions=(httpx.RequestError, httpx.HTTPStatusError)
)
async def get_appointment_details(
    appointment_id: str, jwt_token: str
) -> Optional[Dict[str, Any]]:
    """
    Get appointment details from Appointment Service.

    :param appointment_id: Appointment identifier
    :param jwt_token: JWT authentication token
    :return: Appointment data or None
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.appointment_service_url}/api/v1/appointments/{appointment_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info("appointment_retrieved", appointment_id=appointment_id)
                return response.json()
            else:
                logger.warning("appointment_not_found", appointment_id=appointment_id)
                return None
    except httpx.RequestError as e:
        logger.error("appointment_service_unavailable", error=str(e))
        return None


# Invoice Service Functions


def create_invoice(db: Session, invoice_data: schemas.InvoiceCreate) -> models.Invoice:
    """
    Create new invoice.

    :param db: Database session
    :param invoice_data: Invoice creation data
    :return: Created invoice
    :raises PatientNotFoundError: If patient not found
    :raises ValidationError: If validation fails
    """
    logger.info("creating_invoice", patient_id=invoice_data.subject)

    # Calculate totals
    total_amount = sum(item.line_total.value for item in invoice_data.line_items)

    # Create invoice
    invoice = models.Invoice(
        status=schemas.InvoiceStatusEnum.DRAFT.value,
        subject=invoice_data.subject,
        date=invoice_data.date,
        total_net_amount=total_amount,
        total_gross_amount=total_amount,
        total_paid_amount=Decimal("0.00"),
        total_due_amount=total_amount,
        currency="USD",
        payment_terms=invoice_data.payment_terms,
        notes=invoice_data.notes,
        appointment_id=invoice_data.appointment_id,
        account_id=invoice_data.account_id,
        meta={"created_by": "billing-service"},
    )

    db.add(invoice)
    db.flush()

    # Create line items
    for item_data in invoice_data.line_items:
        line_item = models.InvoiceLineItem(
            invoice_id=invoice.id,
            sequence=item_data.sequence,
            code=item_data.code,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price.value,
            line_total=item_data.line_total.value,
        )
        db.add(line_item)

    db.commit()
    db.refresh(invoice)

    logger.info("invoice_created", invoice_id=str(invoice.id))

    # Publish event
    publish_event(
        "invoice.created",
        {
            "invoice_id": str(invoice.id),
            "patient_id": invoice.subject,
            "amount": float(total_amount),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return invoice


def get_invoice_by_id(db: Session, invoice_id: str) -> models.Invoice:
    """
    Get invoice by ID.

    :param db: Database session
    :param invoice_id: Invoice identifier
    :return: Invoice object
    :raises InvoiceNotFoundError: If invoice not found
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError as exc:
        raise InvoiceNotFoundError(invoice_id) from exc

    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_uuid).first()

    if not invoice:
        raise InvoiceNotFoundError(invoice_id)

    return invoice


def get_invoices_by_patient(
    db: Session, patient_id: str, skip: int = 0, limit: int = 100
) -> List[models.Invoice]:
    """
    Get all invoices for a patient.

    :param db: Database session
    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: List of invoices
    """
    invoices = (
        db.query(models.Invoice)
        .filter(models.Invoice.subject == patient_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return invoices


def update_invoice(
    db: Session, invoice_id: str, invoice_data: schemas.InvoiceUpdate
) -> models.Invoice:
    """
    Update invoice.

    :param db: Database session
    :param invoice_id: Invoice identifier
    :param invoice_data: Invoice update data
    :return: Updated invoice
    :raises InvoiceNotFoundError: If invoice not found
    """
    invoice = get_invoice_by_id(db, invoice_id)

    if invoice_data.status:
        validate_invoice_status_transition(invoice.status, invoice_data.status.value)
        invoice.status = invoice_data.status.value

    if invoice_data.payment_terms is not None:
        invoice.payment_terms = invoice_data.payment_terms

    if invoice_data.notes is not None:
        invoice.notes = invoice_data.notes

    invoice.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(invoice)

    logger.info("invoice_updated", invoice_id=invoice_id)

    return invoice


def update_invoice_status(db: Session, invoice_id: str, status: str) -> models.Invoice:
    """
    Update invoice status.

    :param db: Database session
    :param invoice_id: Invoice identifier
    :param status: New status
    :return: Updated invoice
    :raises InvalidStatusTransitionError: If transition invalid
    """
    invoice = get_invoice_by_id(db, invoice_id)

    validate_invoice_status_transition(invoice.status, status)

    invoice.status = status
    invoice.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(invoice)

    logger.info("invoice_status_updated", invoice_id=invoice_id, status=status)

    return invoice


def validate_invoice_status_transition(current_status: str, new_status: str) -> None:
    """
    Validate invoice status transition.

    :param current_status: Current status
    :param new_status: New status
    :raises InvalidStatusTransitionError: If transition invalid
    """
    valid_transitions = {
        "draft": ["issued", "cancelled"],
        "issued": ["balanced", "cancelled"],
        "balanced": [],
        "cancelled": [],
        "entered-in-error": [],
    }

    if new_status not in valid_transitions.get(current_status, []):
        raise InvalidStatusTransitionError("Invoice", current_status, new_status)


def cancel_invoice(db: Session, invoice_id: str) -> models.Invoice:
    """
    Cancel invoice.

    :param db: Database session
    :param invoice_id: Invoice identifier
    :return: Cancelled invoice
    """
    invoice = update_invoice_status(db, invoice_id, "cancelled")

    # Publish event
    publish_event(
        "invoice.cancelled",
        {
            "invoice_id": invoice_id,
            "patient_id": invoice.subject,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return invoice


# Payment Service Functions


def create_payment(
    db: Session, payment_data: schemas.PaymentRecordCreate
) -> models.PaymentRecord:
    """
    Create payment record.

    :param db: Database session
    :param payment_data: Payment creation data
    :return: Created payment record
    :raises InvoiceNotFoundError: If invoice not found
    :raises ValidationError: If payment exceeds invoice balance
    """
    invoice = get_invoice_by_id(db, payment_data.invoice_id)

    # Validate payment amount doesn't exceed outstanding balance
    outstanding_balance = invoice.total_due_amount - invoice.total_paid_amount
    if payment_data.amount.value > outstanding_balance:
        raise ValidationError(
            f"Payment amount {payment_data.amount.value} exceeds outstanding balance {outstanding_balance}",
            field="amount",
        )

    # Create payment record
    payment = models.PaymentRecord(
        invoice_id=invoice.id,
        amount=payment_data.amount.value,
        currency=payment_data.amount.currency,
        payment_method=payment_data.payment_method,
        payment_date=payment_data.payment_date,
        payment_status=schemas.PaymentStatusEnum.PENDING.value,
        reference_number=payment_data.reference_number,
        notes=payment_data.notes,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Update invoice paid amount
    invoice.total_paid_amount += payment_data.amount.value

    # Update invoice status if fully paid
    if invoice.total_paid_amount >= invoice.total_due_amount:
        invoice.status = schemas.InvoiceStatusEnum.BALANCED.value

    invoice.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(
        "payment_created",
        payment_id=str(payment.id),
        invoice_id=payment_data.invoice_id,
    )

    # Process payment (simulated)
    process_payment(db, payment)

    return payment


def process_payment(db: Session, payment: models.PaymentRecord) -> None:
    """
    Process payment (simulated).

    :param db: Database session
    :param payment: Payment record
    """
    # Simulate payment processing
    payment.payment_status = schemas.PaymentStatusEnum.PAID.value
    payment.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("payment_processed", payment_id=str(payment.id))

    # Publish event
    publish_event(
        "payment.received",
        {
            "payment_id": str(payment.id),
            "invoice_id": str(payment.invoice_id),
            "amount": float(payment.amount),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_payment_by_id(db: Session, payment_id: str) -> models.PaymentRecord:
    """
    Get payment by ID.

    :param db: Database session
    :param payment_id: Payment identifier
    :return: Payment record
    :raises PaymentNotFoundError: If payment not found
    """
    try:
        payment_uuid = uuid.UUID(payment_id)
    except ValueError as exc:
        raise PaymentNotFoundError(payment_id) from exc

    payment = (
        db.query(models.PaymentRecord)
        .filter(models.PaymentRecord.id == payment_uuid)
        .first()
    )

    if not payment:
        raise PaymentNotFoundError(payment_id)

    return payment


def get_payments_by_invoice(db: Session, invoice_id: str) -> List[models.PaymentRecord]:
    """
    Get all payments for an invoice.

    :param db: Database session
    :param invoice_id: Invoice identifier
    :return: List of payments
    """
    invoice = get_invoice_by_id(db, invoice_id)

    payments = (
        db.query(models.PaymentRecord)
        .filter(models.PaymentRecord.invoice_id == invoice.id)
        .all()
    )

    return payments


def update_payment(
    db: Session, payment_id: str, payment_data: schemas.PaymentRecordUpdate
) -> models.PaymentRecord:
    """
    Update payment record.

    :param db: Database session
    :param payment_id: Payment identifier
    :param payment_data: Payment update data
    :return: Updated payment record
    """
    payment = get_payment_by_id(db, payment_id)

    if payment_data.payment_status:
        payment.payment_status = payment_data.payment_status.value

    if payment_data.notes is not None:
        payment.notes = payment_data.notes

    payment.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(payment)

    logger.info("payment_updated", payment_id=payment_id)

    return payment


# Insurance Claim Service Functions


def create_claim(
    db: Session, claim_data: schemas.InsuranceClaimCreate
) -> models.InsuranceClaim:
    """
    Create insurance claim.

    :param db: Database session
    :param claim_data: Claim creation data
    :return: Created claim
    :raises DuplicateResourceError: If claim number already exists
    """
    # Check for duplicate claim number
    existing_claim = (
        db.query(models.InsuranceClaim)
        .filter(models.InsuranceClaim.claim_number == claim_data.claim_number)
        .first()
    )

    if existing_claim:
        raise DuplicateResourceError("Claim", claim_data.claim_number)

    # Calculate total amount
    total_amount = sum(item.net_amount.value for item in claim_data.items)

    # Create claim
    claim = models.InsuranceClaim(
        claim_number=claim_data.claim_number,
        status=schemas.ClaimStatusEnum.DRAFT.value,
        type=claim_data.type,
        patient_id=claim_data.patient_id,
        provider_id=claim_data.provider_id,
        insurer_name=claim_data.insurer_name,
        policy_number=claim_data.policy_number,
        created_date=claim_data.created_date,
        billable_period_start=claim_data.billable_period_start,
        billable_period_end=claim_data.billable_period_end,
        total_amount=total_amount,
        currency="USD",
        claim_items={"items": [item.dict() for item in claim_data.items]},
        meta={"created_by": "billing-service"},
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    logger.info(
        "claim_created", claim_id=str(claim.id), claim_number=claim.claim_number
    )

    return claim


def get_claim_by_id(db: Session, claim_id: str) -> models.InsuranceClaim:
    """
    Get claim by ID.

    :param db: Database session
    :param claim_id: Claim identifier
    :return: Claim object
    :raises ClaimNotFoundError: If claim not found
    """
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError as exc:
        raise ClaimNotFoundError(claim_id) from exc

    claim = (
        db.query(models.InsuranceClaim)
        .filter(models.InsuranceClaim.id == claim_uuid)
        .first()
    )

    if not claim:
        raise ClaimNotFoundError(claim_id)

    return claim


def get_claims_by_patient(
    db: Session, patient_id: str, skip: int = 0, limit: int = 100
) -> List[models.InsuranceClaim]:
    """
    Get all claims for a patient.

    :param db: Database session
    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :return: List of claims
    """
    claims = (
        db.query(models.InsuranceClaim)
        .filter(models.InsuranceClaim.patient_id == patient_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return claims


def update_claim(
    db: Session, claim_id: str, claim_data: schemas.InsuranceClaimUpdate
) -> models.InsuranceClaim:
    """
    Update insurance claim.

    :param db: Database session
    :param claim_id: Claim identifier
    :param claim_data: Claim update data
    :return: Updated claim
    """
    claim = get_claim_by_id(db, claim_id)

    if claim_data.status:
        claim.status = claim_data.status.value

    claim.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(claim)

    logger.info("claim_updated", claim_id=claim_id)

    return claim


# Report Service Functions


def generate_revenue_report(
    db: Session, start_date: datetime, end_date: datetime
) -> schemas.RevenueReportResponse:
    """
    Generate revenue report for date range.

    :param db: Database session
    :param start_date: Report start date
    :param end_date: Report end date
    :return: Revenue report
    """
    invoices = (
        db.query(models.Invoice)
        .filter(
            and_(models.Invoice.date >= start_date, models.Invoice.date <= end_date)
        )
        .all()
    )

    total_revenue = sum(inv.total_gross_amount or 0 for inv in invoices)
    total_paid = sum(inv.total_paid_amount or 0 for inv in invoices)
    total_outstanding = total_revenue - total_paid

    # Group by status
    by_status = {}
    for status in ["draft", "issued", "balanced", "cancelled"]:
        status_invoices = [inv for inv in invoices if inv.status == status]
        by_status[status] = {
            "count": len(status_invoices),
            "amount": {
                "value": sum(inv.total_gross_amount or 0 for inv in status_invoices),
                "currency": "USD",
            },
        }

    return schemas.RevenueReportResponse(
        period_start=start_date,
        period_end=end_date,
        total_invoices=len(invoices),
        total_revenue=schemas.Money(value=Decimal(str(total_revenue)), currency="USD"),
        total_paid=schemas.Money(value=Decimal(str(total_paid)), currency="USD"),
        total_outstanding=schemas.Money(
            value=Decimal(str(total_outstanding)), currency="USD"
        ),
        by_status=by_status,
    )


def get_patient_billing_summary(
    db: Session, patient_id: str
) -> schemas.PatientBillingSummaryResponse:
    """
    Get billing summary for a patient.

    :param db: Database session
    :param patient_id: Patient identifier
    :return: Patient billing summary
    """
    invoices = (
        db.query(models.Invoice).filter(models.Invoice.subject == patient_id).all()
    )

    total_billed = sum(inv.total_gross_amount or 0 for inv in invoices)
    total_paid = sum(inv.total_paid_amount or 0 for inv in invoices)
    total_outstanding = total_billed - total_paid

    return schemas.PatientBillingSummaryResponse(
        patient_id=patient_id,
        total_invoices=len(invoices),
        total_billed=schemas.Money(value=Decimal(str(total_billed)), currency="USD"),
        total_paid=schemas.Money(value=Decimal(str(total_paid)), currency="USD"),
        total_outstanding=schemas.Money(
            value=Decimal(str(total_outstanding)), currency="USD"
        ),
        recent_invoices=[],
        recent_payments=[],
    )
