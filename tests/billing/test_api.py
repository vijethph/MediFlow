"""
API Endpoint Tests for Billing Service.

This module tests REST API endpoints.
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "billing-service"),
)

import schemas


class TestInvoiceEndpoints:
    """Tests for invoice API endpoints."""

    @patch("service.verify_patient_exists")
    def test_create_invoice_success(
        self, mock_verify, authenticated_client, sample_invoice_create, mock_user
    ):
        """Test successful invoice creation."""
        mock_verify.return_value = AsyncMock(return_value=True)

        response = authenticated_client.post(
            "/api/v1/invoices",
            json=sample_invoice_create.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "pat-123"
        assert data["status"] == "draft"

    def test_get_invoice_success(self, authenticated_client, sample_invoice, mock_user):
        """Test retrieving invoice by ID."""

        response = authenticated_client.get(
            f"/api/v1/invoices/{sample_invoice.id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_invoice.id)

    def test_get_invoice_not_found(self, authenticated_client, mock_user):
        """Test retrieving non-existent invoice."""

        response = authenticated_client.get(
            "/api/v1/invoices/00000000-0000-0000-0000-000000000000",
        )

        assert response.status_code == 404

    def test_list_invoices(self, authenticated_client, sample_invoice, mock_user):
        """Test listing invoices by patient."""

        response = authenticated_client.get(
            "/api/v1/invoices?patient_id=pat-123",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_update_invoice(self, authenticated_client, sample_invoice, mock_user):
        """Test updating invoice."""

        update_data = {"status": "issued", "notes": "Updated notes"}

        response = authenticated_client.put(
            f"/api/v1/invoices/{sample_invoice.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "issued"

    def test_cancel_invoice(self, authenticated_client, sample_invoice, mock_user):
        """Test cancelling invoice."""

        # First issue the invoice
        sample_invoice.status = "issued"

        response = authenticated_client.post(
            f"/api/v1/invoices/{sample_invoice.id}/cancel",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestPaymentEndpoints:
    """Tests for payment API endpoints."""

    def test_create_payment_success(
        self, authenticated_client, sample_invoice, sample_payment_create, mock_user
    ):
        """Test successful payment creation."""

        response = authenticated_client.post(
            "/api/v1/payments",
            json=sample_payment_create.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["invoice_id"] == str(sample_invoice.id)
        assert data["payment_status"] == "paid"

    def test_create_payment_exceeds_balance(
        self, authenticated_client, sample_invoice, mock_user
    ):
        """Test payment exceeding invoice balance."""

        payment_data = {
            "invoice_id": str(sample_invoice.id),
            "amount": {"value": 200.00, "currency": "USD"},
            "payment_method": "credit_card",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "reference_number": "PAY-002",
        }

        response = authenticated_client.post(
            "/api/v1/payments",
            json=payment_data,
        )

        assert response.status_code == 400

    def test_get_payment(
        self,
        authenticated_client,
        sample_invoice,
        sample_payment_create,
        mock_user,
        db_session,
    ):
        """Test retrieving payment by ID."""

        # Create payment first
        import service

        payment = service.create_payment(db_session, sample_payment_create)

        response = authenticated_client.get(
            f"/api/v1/payments/{payment.id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(payment.id)

    def test_list_payments(self, authenticated_client, sample_invoice, mock_user):
        """Test listing payments by invoice."""

        response = authenticated_client.get(
            f"/api/v1/payments?invoice_id={sample_invoice.id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert "payments" in data


class TestClaimEndpoints:
    """Tests for insurance claim API endpoints."""

    def test_create_claim_success(
        self, authenticated_client, sample_claim_create, mock_user
    ):
        """Test successful claim creation."""

        response = authenticated_client.post(
            "/api/v1/claims",
            json=sample_claim_create.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["claim_number"] == "CLM-2024-001"
        assert data["status"] == "draft"

    def test_create_duplicate_claim(
        self, authenticated_client, sample_claim_create, mock_user, db_session
    ):
        """Test creating duplicate claim."""

        # Create first claim
        import service

        service.create_claim(db_session, sample_claim_create)

        # Try to create duplicate
        response = authenticated_client.post(
            "/api/v1/claims",
            json=sample_claim_create.model_dump(mode="json"),
        )

        assert response.status_code == 409

    def test_get_claim(
        self, authenticated_client, sample_claim_create, mock_user, db_session
    ):
        """Test retrieving claim by ID."""

        # Create claim
        import service

        claim = service.create_claim(db_session, sample_claim_create)

        response = authenticated_client.get(
            f"/api/v1/claims/{claim.id}", headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(claim.id)

    def test_list_claims(self, authenticated_client, mock_user):
        """Test listing claims by patient."""

        response = authenticated_client.get(
            "/api/v1/claims?patient_id=pat-123",
        )

        assert response.status_code == 200
        data = response.json()
        assert "claims" in data


class TestReportEndpoints:
    """Tests for report API endpoints."""

    def test_revenue_report(self, authenticated_client, mock_user):
        """Test revenue report generation."""

        response = authenticated_client.get(
            "/api/v1/reports/revenue?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59",
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "total_paid" in data

    def test_patient_summary(self, authenticated_client, mock_user):
        """Test patient billing summary."""

        response = authenticated_client.get(
            "/api/v1/reports/patient/pat-123/summary",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == "pat-123"
        assert "total_billed" in data


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "billing-service"
        assert "status" in data
        assert "database" in data
