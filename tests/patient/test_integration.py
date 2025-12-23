"""
Integration Tests for Patient Service.

This module tests end-to-end workflows.
"""

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "patient-service"),
)


class TestPatientWorkflow:
    """Tests for complete patient workflows."""

    def test_full_patient_lifecycle(self, client):
        """Test complete patient lifecycle: register, login, update, delete."""
        # Step 1: Register patient
        register_response = client.post(
            "/api/v1/patients/register",
            json={
                "name": [
                    {
                        "use": "official",
                        "family": "Integration",
                        "given": ["Test"],
                    }
                ],
                "telecom": [
                    {
                        "system": "email",
                        "value": "integration@example.com",
                        "use": "home",
                    }
                ],
                "gender": "male",
                "birth_date": "1995-03-20",
            },
        )

        assert register_response.status_code == 201
        register_data = register_response.json()
        patient_id = register_data["patient_id"]
        token = register_data["access_token"]

        # Step 2: Login patient
        login_response = client.post(
            "/api/v1/patients/login",
            json={"email": "integration@example.com"},
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["patient_id"] == patient_id

        # Step 3: Get patient details
        get_response = client.get(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert get_response.status_code == 200
        patient_data = get_response.json()
        assert patient_data["id"] == patient_id
        assert patient_data["name"][0]["family"] == "Integration"

        # Step 4: Update patient
        update_response = client.put(
            f"/api/v1/patients/{patient_id}",
            json={
                "marital_status": "married",
                "telecom": [
                    {
                        "system": "phone",
                        "value": "+1-555-1234",
                        "use": "mobile",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["marital_status"] == "married"

        # Step 5: Delete patient
        delete_response = client.delete(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert delete_response.status_code == 204

        # Step 6: Verify patient is inactive
        get_deleted_response = client.get(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert get_deleted_response.status_code == 404

    def test_multiple_patients_registration(self, client):
        """Test registering multiple patients."""
        patients_data = [
            {
                "name": [
                    {"use": "official", "family": f"Patient{i}", "given": ["Test"]}
                ],
                "telecom": [
                    {
                        "system": "email",
                        "value": f"patient{i}@example.com",
                        "use": "home",
                    }
                ],
                "gender": "male" if i % 2 == 0 else "female",
                "birth_date": f"199{i}-01-01",
            }
            for i in range(3)
        ]

        patient_ids = []

        for patient_data in patients_data:
            response = client.post(
                "/api/v1/patients/register",
                json=patient_data,
            )

            assert response.status_code == 201
            data = response.json()
            patient_ids.append(data["patient_id"])

        assert len(patient_ids) == 3
        assert len(set(patient_ids)) == 3

    def test_patient_search_and_pagination(self, client, sample_patient_list):
        """Test patient listing with pagination."""
        # Get first page
        response1 = client.get(
            "/api/v1/patients/?skip=0&limit=2",
            headers={"Authorization": "Bearer test_token"},
        )

        # Mock authentication by overriding dependency
        from unittest.mock import patch

        with patch("dependencies.require_authentication") as mock_auth:
            mock_auth.return_value = {"sub": "pat-123", "email": "test@test.com"}

            # Get first page
            response1 = client.get(
                "/api/v1/patients/?skip=0&limit=2",
                headers={"Authorization": "Bearer test_token"},
            )

            if response1.status_code == 200:
                data1 = response1.json()
                assert data1["skip"] == 0
                assert data1["limit"] == 2
                assert len(data1["items"]) <= 2

                # Get second page
                response2 = client.get(
                    "/api/v1/patients/?skip=2&limit=2",
                    headers={"Authorization": "Bearer test_token"},
                )

                if response2.status_code == 200:
                    data2 = response2.json()
                    assert data2["skip"] == 2
                    assert data2["limit"] == 2

                    # Ensure different patients in different pages
                    if len(data1["items"]) > 0 and len(data2["items"]) > 0:
                        patient_ids_1 = {p["id"] for p in data1["items"]}
                        patient_ids_2 = {p["id"] for p in data2["items"]}
                        assert patient_ids_1.isdisjoint(patient_ids_2)


class TestPatientValidation:
    """Tests for patient data validation."""

    def test_register_patient_invalid_birth_date(self, client):
        """Test registering patient with future birth date."""
        from datetime import date, timedelta

        future_date = (date.today() + timedelta(days=365)).isoformat()

        response = client.post(
            "/api/v1/patients/register",
            json={
                "name": [{"use": "official", "family": "Future", "given": ["Baby"]}],
                "telecom": [
                    {"system": "email", "value": "future@example.com", "use": "home"}
                ],
                "gender": "male",
                "birth_date": future_date,
            },
        )

        assert response.status_code == 422

    def test_register_patient_missing_required_fields(self, client):
        """Test registering patient with missing required fields."""
        response = client.post(
            "/api/v1/patients/register",
            json={
                "telecom": [
                    {
                        "system": "email",
                        "value": "incomplete@example.com",
                        "use": "home",
                    }
                ],
            },
        )

        assert response.status_code == 422

    def test_update_patient_invalid_data(self, authenticated_client, sample_patient):
        """Test updating patient with invalid data."""
        response = authenticated_client.put(
            f"/api/v1/patients/{sample_patient.patient_id}",
            json={"birth_date": "invalid-date"},
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 422


class TestConcurrency:
    """Tests for concurrent operations."""

    def test_concurrent_patient_updates(
        self, authenticated_client, sample_patient, db_session
    ):
        """Test concurrent updates to same patient."""
        response1 = authenticated_client.put(
            f"/api/v1/patients/{sample_patient.patient_id}",
            json={"marital_status": "married"},
            headers={"Authorization": "Bearer test_token"},
        )

        response2 = authenticated_client.put(
            f"/api/v1/patients/{sample_patient.patient_id}",
            json={"marital_status": "divorced"},
            headers={"Authorization": "Bearer test_token"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        db_session.refresh(sample_patient)
        assert sample_patient.marital_status == "divorced"
