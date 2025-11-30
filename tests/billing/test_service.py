"""
Service Layer Tests for Billing Service.

This module tests business logic functions.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "billing-service"),
)

import service
import schemas
from common.exceptions import (
    InvoiceNotFoundError,
    PaymentNotFoundError,
    ClaimNotFoundError,
    ValidationError,
    DuplicateResourceError,
    InvalidStatusTransitionError,
)


class TestInvoiceService:
    """Tests for invoice service functions."""

    def test_create_invoice_success(self, db_session, sample_invoice_create):
        """Test successful invoice creation."""
        invoice = service.create_invoice(db_session, sample_invoice_create)

        assert invoice.id is not None
        assert invoice.subject == "pat-123"
        assert invoice.status == "draft"
        assert invoice.total_gross_amount == Decimal("100.00")

    def test_get_invoice_by_id_success(self, db_session, sample_invoice):
        """Test retrieving invoice by ID."""
        invoice = service.get_invoice_by_id(db_session, str(sample_invoice.id))

        assert invoice.id == sample_invoice.id
        assert invoice.subject == sample_invoice.subject

    def test_get_invoice_by_id_not_found(self, db_session):
        """Test retrieving non-existent invoice."""
        with pytest.raises(InvoiceNotFoundError):
            service.get_invoice_by_id(
                db_session, "00000000-0000-0000-0000-000000000000"
            )

    def test_get_invoices_by_patient(self, db_session, sample_invoice):
        """Test listing invoices by patient."""
        invoices = service.get_invoices_by_patient(db_session, "pat-123")

        assert len(invoices) >= 1
        assert all(inv.subject == "pat-123" for inv in invoices)

    def test_update_invoice_success(self, db_session, sample_invoice):
        """Test updating invoice."""
        update_data = schemas.InvoiceUpdate(
            status=schemas.InvoiceStatusEnum.ISSUED, notes="Updated notes"
        )

        updated_invoice = service.update_invoice(
            db_session, str(sample_invoice.id), update_data
        )

        assert updated_invoice.status == "issued"
        assert updated_invoice.notes == "Updated notes"

    def test_cancel_invoice_success(self, db_session, sample_invoice):
        """Test cancelling invoice."""
        sample_invoice.status = "issued"
        db_session.commit()

        cancelled_invoice = service.cancel_invoice(db_session, str(sample_invoice.id))

        assert cancelled_invoice.status == "cancelled"

    def test_invalid_status_transition(self):
        """Test invalid status transition."""
        with pytest.raises(InvalidStatusTransitionError):
            service.validate_invoice_status_transition("balanced", "issued")


class TestPaymentService:
    """Tests for payment service functions."""

    def test_create_payment_success(
        self, db_session, sample_invoice, sample_payment_create
    ):
        """Test successful payment creation."""
        payment = service.create_payment(db_session, sample_payment_create)

        assert payment.id is not None
        assert payment.invoice_id == sample_invoice.id
        assert payment.amount == Decimal("100.00")
        assert payment.payment_status == "paid"

    def test_create_payment_exceeds_balance(self, db_session, sample_invoice):
        """Test payment exceeding invoice balance."""
        payment_data = schemas.PaymentRecordCreate(
            invoice_id=str(sample_invoice.id),
            amount=schemas.Money(value=Decimal("200.00"), currency="USD"),
            payment_method="credit_card",
            payment_date=date.today(),
            reference_number="PAY-002",
        )

        with pytest.raises(ValidationError):
            service.create_payment(db_session, payment_data)

    def test_get_payment_by_id_success(
        self, db_session, sample_invoice, sample_payment_create
    ):
        """Test retrieving payment by ID."""
        payment = service.create_payment(db_session, sample_payment_create)

        retrieved_payment = service.get_payment_by_id(db_session, str(payment.id))

        assert retrieved_payment.id == payment.id

    def test_get_payment_by_id_not_found(self, db_session):
        """Test retrieving non-existent payment."""
        with pytest.raises(PaymentNotFoundError):
            service.get_payment_by_id(
                db_session, "00000000-0000-0000-0000-000000000000"
            )

    def test_get_payments_by_invoice(
        self, db_session, sample_invoice, sample_payment_create
    ):
        """Test listing payments by invoice."""
        service.create_payment(db_session, sample_payment_create)

        payments = service.get_payments_by_invoice(db_session, str(sample_invoice.id))

        assert len(payments) >= 1
        assert all(pay.invoice_id == sample_invoice.id for pay in payments)

    def test_invoice_status_updated_after_payment(
        self, db_session, sample_invoice, sample_payment_create
    ):
        """Test invoice status updates to balanced after full payment."""
        sample_invoice.status = "issued"
        db_session.commit()

        service.create_payment(db_session, sample_payment_create)

        db_session.refresh(sample_invoice)
        assert sample_invoice.status == "balanced"
        assert sample_invoice.total_paid_amount == Decimal("100.00")


class TestClaimService:
    """Tests for insurance claim service functions."""

    def test_create_claim_success(self, db_session, sample_claim_create):
        """Test successful claim creation."""
        claim = service.create_claim(db_session, sample_claim_create)

        assert claim.id is not None
        assert claim.claim_number == "CLM-2024-001"
        assert claim.status == "draft"
        assert claim.total_amount == Decimal("100.00")

    def test_create_duplicate_claim(self, db_session, sample_claim_create):
        """Test creating duplicate claim."""
        service.create_claim(db_session, sample_claim_create)

        with pytest.raises(DuplicateResourceError):
            service.create_claim(db_session, sample_claim_create)

    def test_get_claim_by_id_success(self, db_session, sample_claim_create):
        """Test retrieving claim by ID."""
        claim = service.create_claim(db_session, sample_claim_create)

        retrieved_claim = service.get_claim_by_id(db_session, str(claim.id))

        assert retrieved_claim.id == claim.id

    def test_get_claim_by_id_not_found(self, db_session):
        """Test retrieving non-existent claim."""
        with pytest.raises(ClaimNotFoundError):
            service.get_claim_by_id(db_session, "00000000-0000-0000-0000-000000000000")

    def test_get_claims_by_patient(self, db_session, sample_claim_create):
        """Test listing claims by patient."""
        service.create_claim(db_session, sample_claim_create)

        claims = service.get_claims_by_patient(db_session, "pat-123")

        assert len(claims) >= 1
        assert all(claim.patient_id == "pat-123" for claim in claims)

    def test_update_claim_success(self, db_session, sample_claim_create):
        """Test updating claim."""
        claim = service.create_claim(db_session, sample_claim_create)

        update_data = schemas.InsuranceClaimUpdate(
            status=schemas.ClaimStatusEnum.ACTIVE
        )

        updated_claim = service.update_claim(db_session, str(claim.id), update_data)

        assert updated_claim.status == "active"


class TestReportService:
    """Tests for report service functions."""

    def test_generate_revenue_report(self, db_session, sample_invoice):
        """Test revenue report generation."""
        from datetime import datetime, timedelta

        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        report = service.generate_revenue_report(db_session, start_date, end_date)

        assert report.total_revenue.value >= 0
        assert report.total_paid.value >= 0
        assert report.total_outstanding.value >= 0
        assert "draft" in report.by_status

    def test_get_patient_billing_summary(self, db_session, sample_invoice):
        """Test patient billing summary."""
        summary = service.get_patient_billing_summary(db_session, "pat-123")

        assert summary.patient_id == "pat-123"
        assert summary.total_invoices >= 1
        assert summary.total_billed.value >= 0
