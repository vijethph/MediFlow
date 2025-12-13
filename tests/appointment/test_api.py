"""
API Endpoint Tests for Appointment Service.

This module tests REST API endpoints.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "services", "appointment-service"
    ),
)

import schemas


class TestAppointmentEndpoints:
    """Tests for appointment API endpoints."""

    @patch("service.verify_patient_exists")
    @patch("dependencies.require_authentication")
    def test_create_appointment_success(
        self, mock_auth, mock_verify, client, sample_appointment_create, mock_user
    ):
        """Test successful appointment creation."""
        mock_auth.return_value = mock_user
        mock_verify.return_value = AsyncMock(return_value=True)

        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = appointment_dict["start"].isoformat()
        appointment_dict["end"] = appointment_dict["end"].isoformat()

        response = client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "booked"
        assert data["description"] == "Annual checkup"

    @patch("dependencies.require_authentication")
    def test_create_appointment_unauthorized(self, mock_auth, client):
        """Test appointment creation without authentication."""
        mock_auth.side_effect = Exception("Unauthorized")

        response = client.post("/api/v1/appointments", json={})

        assert response.status_code in [401, 403, 500]

    @patch("dependencies.require_authentication")
    def test_get_appointment_success(
        self, mock_auth, client, sample_appointment, mock_user
    ):
        """Test retrieving appointment by ID."""
        mock_auth.return_value = mock_user

        response = client.get(
            f"/api/v1/appointments/{sample_appointment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_appointment.id)
        assert data["status"] == sample_appointment.status

    @patch("dependencies.require_authentication")
    def test_get_appointment_not_found(self, mock_auth, client, mock_user):
        """Test retrieving non-existent appointment."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("dependencies.require_authentication")
    def test_list_appointments(self, mock_auth, client, sample_appointment, mock_user):
        """Test listing appointments."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    @patch("dependencies.require_authentication")
    def test_list_appointments_by_patient(
        self, mock_auth, client, sample_appointment, mock_user
    ):
        """Test listing appointments by patient ID."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments?patient_id=pat-123",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @patch("dependencies.require_authentication")
    def test_list_appointments_by_practitioner(
        self, mock_auth, client, sample_appointment, mock_user
    ):
        """Test listing appointments by practitioner ID."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments?practitioner_id=prac-456",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @patch("dependencies.require_authentication")
    def test_list_appointments_by_status(
        self, mock_auth, client, sample_appointment, mock_user
    ):
        """Test listing appointments by status."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments?appointment_status=booked",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @patch("dependencies.require_authentication")
    def test_list_appointments_with_pagination(
        self, mock_auth, client, sample_appointment, mock_user
    ):
        """Test appointment list pagination."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/appointments?skip=0&limit=5",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["skip"] == 0
        assert data["limit"] == 5

    @patch("dependencies.require_authentication")
    def test_update_appointment(self, mock_auth, client, sample_appointment, mock_user):
        """Test updating appointment."""
        mock_auth.return_value = mock_user

        update_data = {
            "status": "fulfilled",
            "comment": "Patient arrived on time",
        }

        response = client.put(
            f"/api/v1/appointments/{sample_appointment.id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fulfilled"
        assert data["comment"] == "Patient arrived on time"

    @patch("dependencies.require_authentication")
    def test_update_appointment_not_found(self, mock_auth, client, mock_user):
        """Test updating non-existent appointment."""
        mock_auth.return_value = mock_user

        update_data = {"status": "fulfilled"}

        response = client.put(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("dependencies.require_authentication")
    def test_delete_appointment(self, mock_auth, client, sample_appointment, mock_user):
        """Test deleting appointment."""
        mock_auth.return_value = mock_user

        response = client.delete(
            f"/api/v1/appointments/{sample_appointment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 204

    @patch("dependencies.require_authentication")
    def test_delete_appointment_not_found(self, mock_auth, client, mock_user):
        """Test deleting non-existent appointment."""
        mock_auth.return_value = mock_user

        response = client.delete(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("dependencies.require_authentication")
    def test_cancel_appointment(self, mock_auth, client, sample_appointment, mock_user):
        """Test cancelling appointment."""
        mock_auth.return_value = mock_user

        response = client.post(
            f"/api/v1/appointments/{sample_appointment.id}/cancel",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @patch("dependencies.require_authentication")
    def test_cancel_appointment_not_found(self, mock_auth, client, mock_user):
        """Test cancelling non-existent appointment."""
        mock_auth.return_value = mock_user

        response = client.post(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000/cancel",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("dependencies.require_authentication")
    def test_appointment_validation_past_date(
        self, mock_auth, client, mock_user, sample_appointment_create
    ):
        """Test appointment creation with past date fails validation."""
        mock_auth.return_value = mock_user

        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = (datetime.now() - timedelta(days=1)).isoformat()
        appointment_dict["end"] = datetime.now().isoformat()

        response = client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code in [400, 422]

    @patch("dependencies.require_authentication")
    def test_appointment_validation_end_before_start(
        self, mock_auth, client, mock_user, sample_appointment_create
    ):
        """Test appointment creation with end before start fails validation."""
        mock_auth.return_value = mock_user

        appointment_dict = sample_appointment_create.model_dump()
        start_time = datetime.now() + timedelta(days=7)
        appointment_dict["start"] = start_time.isoformat()
        appointment_dict["end"] = (start_time - timedelta(hours=1)).isoformat()

        response = client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code in [400, 422]
