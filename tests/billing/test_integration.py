"""
Integration Tests for Billing Service.

This module tests external service integrations and event handling.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "billing-service"),
)

import service
from common.exceptions import PatientNotFoundError, ServiceUnavailableError


class TestExternalServiceIntegration:
    """Tests for external service API calls."""

    @pytest.mark.asyncio
    @patch("services.billing_service.service.httpx.AsyncClient")
    async def test_verify_patient_exists_success(self, mock_client):
        """Test successful patient verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "pat-123", "name": "John Doe"}

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_context

        result = await service.verify_patient_exists("pat-123", "test_token")

        assert result is True

    @pytest.mark.asyncio
    @patch("services.billing_service.service.httpx.AsyncClient")
    async def test_verify_patient_not_found(self, mock_client):
        """Test patient not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_context

        with pytest.raises(PatientNotFoundError):
            await service.verify_patient_exists("pat-999", "test_token")

    @pytest.mark.asyncio
    @patch("services.billing_service.service.httpx.AsyncClient")
    async def test_get_appointment_details_success(self, mock_client):
        """Test successful appointment retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "appt-123",
            "patient_id": "pat-123",
            "status": "booked",
        }

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_context

        result = await service.get_appointment_details("appt-123", "test_token")

        assert result is not None
        assert result["id"] == "appt-123"

    @pytest.mark.asyncio
    @patch("services.billing_service.service.httpx.AsyncClient")
    async def test_get_appointment_not_found(self, mock_client):
        """Test appointment not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_context

        result = await service.get_appointment_details("appt-999", "test_token")

        assert result is None


class TestEventPublishing:
    """Tests for RabbitMQ event publishing."""

    @patch("service.publish_event")
    def test_invoice_created_event(
        self, mock_publish, db_session, sample_invoice_create
    ):
        """Test invoice.created event is published."""
        service.create_invoice(db_session, sample_invoice_create)

        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "invoice.created"

    @patch("service.publish_event")
    def test_payment_received_event(
        self, mock_publish, db_session, sample_invoice, sample_payment_create
    ):
        """Test payment.received event is published."""
        service.create_payment(db_session, sample_payment_create)

        mock_publish.assert_called()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "payment.received"

    @patch("services.billing_service.service.publish_event")
    def test_invoice_cancelled_event(self, mock_publish, db_session, sample_invoice):
        """Test invoice.cancelled event is published."""
        sample_invoice.status = "issued"
        db_session.commit()

        service.cancel_invoice(db_session, str(sample_invoice.id))

        mock_publish.assert_called()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "invoice.cancelled"


class TestRetryLogic:
    """Tests for retry mechanisms on external calls."""

    @pytest.mark.asyncio
    @patch("services.billing_service.service.httpx.AsyncClient")
    async def test_retry_on_service_unavailable(self, mock_client):
        """Test retry logic when service unavailable."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_context

        with pytest.raises(ServiceUnavailableError):
            await service.verify_patient_exists("pat-123", "test_token")
