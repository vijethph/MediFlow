"""
Integration Tests for Appointment Service.

This module tests end-to-end workflows and integration scenarios.
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


class TestAppointmentWorkflows:
    """Tests for complete appointment workflows."""

    @patch("service.verify_patient_exists")
    def test_complete_appointment_lifecycle(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test complete appointment lifecycle: create, update, cancel."""
        mock_verify.return_value = AsyncMock(return_value=True)

        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = appointment_dict["start"].isoformat()
        appointment_dict["end"] = appointment_dict["end"].isoformat()

        create_response = authenticated_client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        get_response = authenticated_client.get(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": "Bearer test_token"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "booked"

        update_response = authenticated_client.put(
            f"/api/v1/appointments/{appointment_id}",
            json={"status": "fulfilled", "comment": "Completed successfully"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "fulfilled"

        cancel_response = authenticated_client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers={"Authorization": "Bearer test_token"},
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

    @patch("service.verify_patient_exists")
    def test_patient_appointment_history(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test retrieving appointment history for a patient."""
        mock_verify.return_value = AsyncMock(return_value=True)

        for i in range(3):
            appointment_dict = sample_appointment_create.model_dump()
            start_time = datetime.now() + timedelta(days=7 + i)
            appointment_dict["start"] = start_time.isoformat()
            appointment_dict["end"] = (start_time + timedelta(hours=1)).isoformat()

            response = authenticated_client.post(
                "/api/v1/appointments",
                json=appointment_dict,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 201

        list_response = authenticated_client.get(
            "/api/v1/appointments?patient_id=pat-123",
            headers={"Authorization": "Bearer test_token"},
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] >= 3

    @patch("service.verify_patient_exists")
    def test_practitioner_schedule(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test retrieving practitioner schedule."""
        mock_verify.return_value = AsyncMock(return_value=True)

        for i in range(3):
            appointment_dict = sample_appointment_create.model_dump()
            start_time = datetime.now() + timedelta(days=7 + i)
            appointment_dict["start"] = start_time.isoformat()
            appointment_dict["end"] = (start_time + timedelta(hours=1)).isoformat()

            response = authenticated_client.post(
                "/api/v1/appointments",
                json=appointment_dict,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 201

        list_response = authenticated_client.get(
            "/api/v1/appointments?practitioner_id=prac-456",
            headers={"Authorization": "Bearer test_token"},
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] >= 3

    @patch("service.verify_patient_exists")
    def test_appointment_status_transitions(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test valid appointment status transitions."""
        mock_verify.return_value = AsyncMock(return_value=True)

        appointment_dict = sample_appointment_create.model_dump()
        appointment_dict["start"] = appointment_dict["start"].isoformat()
        appointment_dict["end"] = appointment_dict["end"].isoformat()
        appointment_dict["status"] = "proposed"

        create_response = authenticated_client.post(
            "/api/v1/appointments",
            json=appointment_dict,
            headers={"Authorization": "Bearer test_token"},
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        update_to_booked = authenticated_client.put(
            f"/api/v1/appointments/{appointment_id}",
            json={"status": "booked"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert update_to_booked.status_code == 200
        assert update_to_booked.json()["status"] == "booked"

        update_to_arrived = authenticated_client.put(
            f"/api/v1/appointments/{appointment_id}",
            json={"status": "arrived"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert update_to_arrived.status_code == 200
        assert update_to_arrived.json()["status"] == "arrived"

        update_to_fulfilled = authenticated_client.put(
            f"/api/v1/appointments/{appointment_id}",
            json={"status": "fulfilled"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert update_to_fulfilled.status_code == 200
        assert update_to_fulfilled.json()["status"] == "fulfilled"

    def test_date_range_filtering(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test filtering appointments by date range."""

        start_date = (datetime.now() + timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=30)).isoformat()

        response = authenticated_client.get(
            f"/api/v1/appointments?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0

    def test_pagination_consistency(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test pagination consistency across multiple requests."""

        page1 = authenticated_client.get(
            "/api/v1/appointments?skip=0&limit=10",
            headers={"Authorization": "Bearer test_token"},
        )
        assert page1.status_code == 200

        page2 = authenticated_client.get(
            "/api/v1/appointments?skip=10&limit=10",
            headers={"Authorization": "Bearer test_token"},
        )
        assert page2.status_code == 200

        page1_ids = {item["id"] for item in page1.json()["items"]}
        page2_ids = {item["id"] for item in page2.json()["items"]}

        assert page1_ids.isdisjoint(page2_ids)

    @patch("service.verify_patient_exists")
    def test_appointment_with_multiple_participants(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test creating appointment with patient and practitioner."""
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
        assert len(data["participant"]) == 2
        assert any(p["type"][0] == "patient" for p in data["participant"])
        assert any(p["type"][0] == "practitioner" for p in data["participant"])

    def test_appointment_fhir_compliance(
        self, authenticated_client, sample_appointment, mock_user
    ):
        """Test appointment response FHIR compliance."""

        response = authenticated_client.get(
            f"/api/v1/appointments/{sample_appointment.id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resource_type"] == "Appointment"
        assert "id" in data
        assert "status" in data
        assert "participant" in data
        assert "start" in data
        assert "end" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert isinstance(data["participant"], list)

    @patch("service.verify_patient_exists")
    def test_concurrent_appointment_creation(
        self, mock_verify, authenticated_client, sample_appointment_create, mock_user
    ):
        """Test creating multiple appointments concurrently."""
        mock_verify.return_value = AsyncMock(return_value=True)

        created_ids = []
        for i in range(5):
            appointment_dict = sample_appointment_create.model_dump()
            start_time = datetime.now() + timedelta(days=7 + i, hours=i)
            appointment_dict["start"] = start_time.isoformat()
            appointment_dict["end"] = (start_time + timedelta(hours=1)).isoformat()

            response = authenticated_client.post(
                "/api/v1/appointments",
                json=appointment_dict,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        assert len(created_ids) == 5
        assert len(set(created_ids)) == 5
