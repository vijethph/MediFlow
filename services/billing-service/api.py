"""
API Routes for Billing Service.

This module defines REST API endpoints for invoices, payments, and claims.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

import schemas
import service
from common.exceptions import (
    ClaimNotFoundError,
    DuplicateResourceError,
    InvoiceNotFoundError,
    PatientNotFoundError,
    PaymentNotFoundError,
    ValidationError,
)
from common.logging import get_logger
from database import get_db
from dependencies import require_authentication


router = APIRouter()
logger = get_logger(__name__)


# Invoice Endpoints


@router.post(
    "/invoices",
    response_model=schemas.InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Invoices"],
    summary="Create a new invoice",
)
async def create_invoice(
    invoice_data: schemas.InvoiceCreate,
    current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Create a new invoice for a patient.

    :param invoice_data: Invoice creation data
    :param request: FastAPI request object
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created invoice
    """
    logger.info(
        "api_create_invoice",
        patient_id=invoice_data.subject,
        user_id=current_user.get("sub"),
    )

    try:
        invoice = service.create_invoice(db, invoice_data)
        return schemas.InvoiceResponse.from_orm(invoice)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get(
    "/invoices/{invoice_id}",
    response_model=schemas.InvoiceResponse,
    tags=["Invoices"],
    summary="Get invoice by ID",
)
def delete_invoice(
    invoice_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Retrieve invoice by ID.

    :param invoice_id: Invoice identifier
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Invoice details
    """
    logger.info("api_get_invoice", invoice_id=invoice_id)

    try:
        invoice = service.get_invoice_by_id(db, invoice_id)
        return schemas.InvoiceResponse.from_orm(invoice)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/invoices",
    response_model=schemas.InvoiceListResponse,
    tags=["Invoices"],
    summary="List invoices by patient",
)
def list_invoices(
    patient_id: str = Query(..., description="Patient ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List all invoices for a patient.

    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of invoices
    """
    logger.info("api_list_invoices", patient_id=patient_id, skip=skip, limit=limit)

    invoices = service.get_invoices_by_patient(db, patient_id, skip, limit)

    return schemas.InvoiceListResponse(
        total=len(invoices),
        count=len(invoices),
        items=[schemas.InvoiceResponse.from_orm(inv) for inv in invoices],
    )


@router.put(
    "/invoices/{invoice_id}",
    response_model=schemas.InvoiceResponse,
    tags=["Invoices"],
    summary="Update invoice",
)
def update_invoice(
    invoice_id: str,
    invoice_update: schemas.InvoiceUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Update invoice details.

    :param invoice_id: Invoice identifier
    :param invoice_data: Invoice update data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated invoice
    """
    logger.info("api_update_invoice", invoice_id=invoice_id)

    try:
        invoice = service.update_invoice(db, invoice_id, invoice_update)
        return schemas.InvoiceResponse.from_orm(invoice)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=schemas.InvoiceResponse,
    tags=["Invoices"],
    summary="Cancel invoice",
)
def cancel_invoice(
    invoice_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Cancel an invoice.

    :param invoice_id: Invoice identifier
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Cancelled invoice
    """
    logger.info("api_cancel_invoice", invoice_id=invoice_id)

    try:
        service.delete_invoice(db, invoice_id)
        return {"message": "Invoice deleted successfully"}
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Payment Endpoints


@router.post(
    "/payments",
    response_model=schemas.PaymentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Payments"],
    summary="Create a new payment",
)
def create_payment(
    payment_data: schemas.PaymentRecordCreate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Create a new payment record.

    :param payment_data: Payment creation data
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created payment
    """
    logger.info("api_create_payment", invoice_id=payment_data.invoice_id)

    try:
        payment = service.create_payment(db, payment_data)
        return schemas.PaymentRecordResponse.from_orm(payment)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/payments/{payment_id}",
    response_model=schemas.PaymentRecordResponse,
    tags=["Payments"],
    summary="Get payment by ID",
)
def get_payment(
    payment_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Retrieve payment by ID.

    :param payment_id: Payment identifier
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Payment details
    """
    logger.info("api_get_payment", payment_id=payment_id)

    try:
        payment = service.get_payment_by_id(db, payment_id)
        return schemas.PaymentRecordResponse.from_orm(payment)
    except PaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/payments",
    response_model=schemas.PaymentRecordListResponse,
    tags=["Payments"],
    summary="List payments by invoice",
)
def list_payments(
    invoice_id: str = Query(..., description="Invoice ID to filter payments"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List all payments for an invoice.

    :param invoice_id: Invoice identifier
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of payments
    """
    logger.info("api_list_payments", invoice_id=invoice_id)

    try:
        payments = service.get_payments_by_invoice(db, invoice_id)
        return schemas.PaymentRecordListResponse(
            total=len(payments),
            payments=[schemas.PaymentRecordResponse.from_orm(pay) for pay in payments],
        )
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put(
    "/payments/{payment_id}",
    response_model=schemas.PaymentRecordResponse,
    tags=["Payments"],
    summary="Update payment",
)
def update_payment(
    payment_id: str,
    payment_data: schemas.PaymentRecordUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Update payment record.

    :param payment_id: Payment identifier
    :param payment_data: Payment update data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated payment
    """
    logger.info("api_update_payment", payment_id=payment_id)

    try:
        payment = service.update_payment(db, payment_id, payment_data)
        return schemas.PaymentRecordResponse.from_orm(payment)
    except PaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Insurance Claim Endpoints


@router.post(
    "/claims",
    response_model=schemas.InsuranceClaimResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Claims"],
    summary="Create a new insurance claim",
)
def create_claim(
    claim_data: schemas.InsuranceClaimCreate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Create a new insurance claim.

    :param claim_data: Claim creation data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Created claim
    """
    logger.info("api_create_claim", claim_number=claim_data.claim_number)

    try:
        claim = service.create_claim(db, claim_data)
        return schemas.InsuranceClaimResponse.from_orm(claim)
    except DuplicateResourceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get(
    "/claims/{claim_id}",
    response_model=schemas.InsuranceClaimResponse,
    tags=["Claims"],
    summary="Get claim by ID",
)
def get_claim(
    claim_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Retrieve claim by ID.

    :param claim_id: Claim identifier
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Claim details
    """
    logger.info("api_get_claim", claim_id=claim_id)

    try:
        claim = service.get_claim_by_id(db, claim_id)
        return schemas.InsuranceClaimResponse.from_orm(claim)
    except ClaimNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/claims",
    response_model=schemas.InsuranceClaimListResponse,
    tags=["Claims"],
    summary="List claims by patient",
)
def list_claims(
    patient_id: str = Query(..., description="Patient ID to filter claims"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List all claims for a patient.

    :param patient_id: Patient identifier
    :param skip: Number of records to skip
    :param limit: Maximum records to return
    :param _current_user: Authenticated user from JWT
    :param db: Database session
    :return: List of claims
    """
    logger.info("api_list_claims", patient_id=patient_id, skip=skip, limit=limit)

    claims = service.get_claims_by_patient(db, patient_id, skip, limit)

    return schemas.InsuranceClaimListResponse(
        total=len(claims),
        claims=[schemas.InsuranceClaimResponse.from_orm(claim) for claim in claims],
    )


@router.put(
    "/claims/{claim_id}",
    response_model=schemas.InsuranceClaimResponse,
    tags=["Claims"],
    summary="Update claim",
)
def update_claim(
    claim_id: str,
    claim_data: schemas.InsuranceClaimUpdate,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Update insurance claim.

    :param claim_id: Claim identifier
    :param claim_data: Claim update data
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Updated claim
    """
    logger.info("api_update_claim", claim_id=claim_id)

    try:
        claim = service.update_claim(db, claim_id, claim_data)
        return schemas.InsuranceClaimResponse.from_orm(claim)
    except ClaimNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Report Endpoints


@router.get(
    "/reports/revenue",
    response_model=schemas.RevenueReportResponse,
    tags=["Reports"],
    summary="Generate revenue report",
)
def generate_revenue_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Generate revenue report for date range.

    :param start_date: Report start date
    :param end_date: Report end date
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Revenue report
    """
    logger.info("api_revenue_report", start_date=start_date, end_date=end_date)

    return service.generate_revenue_report(db, start_date, end_date)


@router.get(
    "/reports/patient/{patient_id}/summary",
    response_model=schemas.PatientBillingSummaryResponse,
    tags=["Reports"],
    summary="Get patient billing summary",
)
def get_patient_summary(
    patient_id: str,
    _current_user: dict = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Get billing summary for a patient.

    :param patient_id: Patient identifier
    :param current_user: Authenticated user from JWT
    :param db: Database session
    :return: Patient billing summary
    """
    logger.info("api_patient_summary", patient_id=patient_id)

    return service.get_patient_billing_summary(db, patient_id)
