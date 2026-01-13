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
    def test_create_appointment_success(
        self, mock_verify, authenticated_client, sample_appointment_create
    ):
        """Test successful appointment creation."""
        mock_verify.return_value = AsyncMock(return_value=True)

        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = appointment_dict["start"].isoformat()
        appointment_dict["end"] = appointment_dict["end"].isoformat()

        response = authenticated_client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "booked"
        assert data["description"] == "Annual checkup"

    def test_create_appointment_unauthorized(self, client):
        """Test appointment creation without authentication."""
        response = client.post("/api/v1/appointments", json={})

        assert response.status_code in [401, 403, 500]

    def test_get_appointment_success(self, authenticated_client, sample_appointment):
        """Test retrieving appointment by ID."""
        response = authenticated_client.get(
            f"/api/v1/appointments/{sample_appointment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_appointment.id)
        assert data["status"] == sample_appointment.status

    def test_get_appointment_not_found(self, authenticated_client):
        """Test retrieving non-existent appointment."""
        response = authenticated_client.get(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_list_appointments(self, authenticated_client, sample_appointment):
        """Test listing appointments."""
        response = authenticated_client.get(
            "/api/v1/appointments",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    def test_list_appointments_by_patient(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test listing appointments by patient ID."""
        response = authenticated_client.get(
            "/api/v1/appointments?patient_id=pat-123",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_appointments_by_practitioner(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test listing appointments by practitioner ID."""
        response = authenticated_client.get(
            "/api/v1/appointments?practitioner_id=prac-456",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_appointments_by_status(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test listing appointments by status."""
        response = authenticated_client.get(
            "/api/v1/appointments?appointment_status=booked",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_appointments_with_pagination(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test appointment list pagination."""
        response = authenticated_client.get(
            "/api/v1/appointments?skip=0&limit=5",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["skip"] == 0
        assert data["limit"] == 5

    def test_update_appointment(self, authenticated_client, sample_appointment):
        """Test updating appointment."""
        update_data = {
            "status": "fulfilled",
            "comment": "Patient arrived on time",
        }

        response = authenticated_client.put(
            f"/api/v1/appointments/{sample_appointment.id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fulfilled"
        assert data["comment"] == "Patient arrived on time"

    def test_update_appointment_not_found(self, authenticated_client):
        """Test updating non-existent appointment."""
        update_data = {"status": "fulfilled"}

        response = authenticated_client.put(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_delete_appointment(self, authenticated_client, sample_appointment):
        """Test deleting appointment."""
        response = authenticated_client.delete(
            f"/api/v1/appointments/{sample_appointment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 204

    def test_delete_appointment_not_found(self, authenticated_client):
        """Test deleting non-existent appointment."""
        response = authenticated_client.delete(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_cancel_appointment(self, authenticated_client, sample_appointment):
        """Test cancelling appointment."""
        response = authenticated_client.post(
            f"/api/v1/appointments/{sample_appointment.id}/cancel",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_appointment_not_found(self, authenticated_client):
        """Test cancelling non-existent appointment."""
        response = authenticated_client.post(
            "/api/v1/appointments/00000000-0000-0000-0000-000000000000/cancel",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_appointment_validation_past_date(
        self, authenticated_client, mock_user, sample_appointment_create
    ):
        """Test appointment creation with past date fails validation."""
        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = (datetime.now() - timedelta(days=1)).isoformat()
        appointment_dict["end"] = datetime.now().isoformat()

        response = authenticated_client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code in [400, 422]

    def test_appointment_validation_end_before_start(
        self, authenticated_client, mock_user, sample_appointment_create
    ):
        """Test appointment creation with end before start fails validation."""
        appointment_dict = sample_appointment_create.model_dump()
        start_time = datetime.now() + timedelta(days=7)
        appointment_dict["start"] = start_time.isoformat()
        appointment_dict["end"] = (start_time - timedelta(hours=1)).isoformat()

        response = authenticated_client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code in [400, 422]
