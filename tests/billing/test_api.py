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

from services.billing_service import schemas


class TestInvoiceEndpoints:
    """Tests for invoice API endpoints."""

    @patch("services.billing_service.service.verify_patient_exists")
    @patch("services.billing_service.dependencies.require_authentication")
    def test_create_invoice_success(
        self, mock_auth, mock_verify, client, sample_invoice_create, mock_user
    ):
        """Test successful invoice creation."""
        mock_auth.return_value = mock_user
        mock_verify.return_value = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/invoices",
            json=sample_invoice_create.dict(),
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "pat-123"
        assert data["status"] == "draft"

    @patch("services.billing_service.dependencies.require_authentication")
    def test_get_invoice_success(self, mock_auth, client, sample_invoice, mock_user):
        """Test retrieving invoice by ID."""
        mock_auth.return_value = mock_user

        response = client.get(
            f"/api/v1/invoices/{sample_invoice.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_invoice.id)

    @patch("services.billing_service.dependencies.require_authentication")
    def test_get_invoice_not_found(self, mock_auth, client, mock_user):
        """Test retrieving non-existent invoice."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/invoices/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("services.billing_service.dependencies.require_authentication")
    def test_list_invoices(self, mock_auth, client, sample_invoice, mock_user):
        """Test listing invoices by patient."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/invoices?patient_id=pat-123",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @patch("services.billing_service.dependencies.require_authentication")
    def test_update_invoice(self, mock_auth, client, sample_invoice, mock_user):
        """Test updating invoice."""
        mock_auth.return_value = mock_user

        update_data = {"status": "issued", "notes": "Updated notes"}

        response = client.put(
            f"/api/v1/invoices/{sample_invoice.id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "issued"

    @patch("services.billing_service.dependencies.require_authentication")
    def test_cancel_invoice(self, mock_auth, client, sample_invoice, mock_user):
        """Test cancelling invoice."""
        mock_auth.return_value = mock_user

        # First issue the invoice
        sample_invoice.status = "issued"

        response = client.post(
            f"/api/v1/invoices/{sample_invoice.id}/cancel",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestPaymentEndpoints:
    """Tests for payment API endpoints."""

    @patch("services.billing_service.dependencies.require_authentication")
    def test_create_payment_success(
        self, mock_auth, client, sample_invoice, sample_payment_create, mock_user
    ):
        """Test successful payment creation."""
        mock_auth.return_value = mock_user

        response = client.post(
            "/api/v1/payments",
            json=sample_payment_create.dict(),
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["invoice_id"] == str(sample_invoice.id)
        assert data["payment_status"] == "paid"

    @patch("services.billing_service.dependencies.require_authentication")
    def test_create_payment_exceeds_balance(
        self, mock_auth, client, sample_invoice, mock_user
    ):
        """Test payment exceeding invoice balance."""
        mock_auth.return_value = mock_user

        payment_data = {
            "invoice_id": str(sample_invoice.id),
            "amount": {"value": 200.00, "currency": "USD"},
            "payment_method": "credit_card",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "reference_number": "PAY-002",
        }

        response = client.post(
            "/api/v1/payments",
            json=payment_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 400

    @patch("services.billing_service.dependencies.require_authentication")
    def test_get_payment(
        self,
        mock_auth,
        client,
        sample_invoice,
        sample_payment_create,
        mock_user,
        db_session,
    ):
        """Test retrieving payment by ID."""
        mock_auth.return_value = mock_user

        # Create payment first
        from services.billing_service import service

        payment = service.create_payment(db_session, sample_payment_create)

        response = client.get(
            f"/api/v1/payments/{payment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(payment.id)

    @patch("services.billing_service.dependencies.require_authentication")
    def test_list_payments(self, mock_auth, client, sample_invoice, mock_user):
        """Test listing payments by invoice."""
        mock_auth.return_value = mock_user

        response = client.get(
            f"/api/v1/payments?invoice_id={sample_invoice.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "payments" in data


class TestClaimEndpoints:
    """Tests for insurance claim API endpoints."""

    @patch("services.billing_service.dependencies.require_authentication")
    def test_create_claim_success(
        self, mock_auth, client, sample_claim_create, mock_user
    ):
        """Test successful claim creation."""
        mock_auth.return_value = mock_user

        response = client.post(
            "/api/v1/claims",
            json=sample_claim_create.dict(),
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["claim_number"] == "CLM-2024-001"
        assert data["status"] == "draft"

    @patch("services.billing_service.dependencies.require_authentication")
    def test_create_duplicate_claim(
        self, mock_auth, client, sample_claim_create, mock_user, db_session
    ):
        """Test creating duplicate claim."""
        mock_auth.return_value = mock_user

        # Create first claim
        from services.billing_service import service

        service.create_claim(db_session, sample_claim_create)

        # Try to create duplicate
        response = client.post(
            "/api/v1/claims",
            json=sample_claim_create.dict(),
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 409

    @patch("services.billing_service.dependencies.require_authentication")
    def test_get_claim(
        self, mock_auth, client, sample_claim_create, mock_user, db_session
    ):
        """Test retrieving claim by ID."""
        mock_auth.return_value = mock_user

        # Create claim
        from services.billing_service import service

        claim = service.create_claim(db_session, sample_claim_create)

        response = client.get(
            f"/api/v1/claims/{claim.id}", headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(claim.id)

    @patch("services.billing_service.dependencies.require_authentication")
    def test_list_claims(self, mock_auth, client, mock_user):
        """Test listing claims by patient."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/claims?patient_id=pat-123",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "claims" in data


class TestReportEndpoints:
    """Tests for report API endpoints."""

    @patch("services.billing_service.dependencies.require_authentication")
    def test_revenue_report(self, mock_auth, client, mock_user):
        """Test revenue report generation."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/reports/revenue?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "total_paid" in data

    @patch("services.billing_service.dependencies.require_authentication")
    def test_patient_summary(self, mock_auth, client, mock_user):
        """Test patient billing summary."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/reports/patient/pat-123/summary",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == "pat-123"
        assert "total_billed" in data


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "billing-service"
        assert "status" in data
        assert "database" in data
