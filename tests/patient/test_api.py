"""
API Endpoint Tests for Patient Service.

This module tests REST API endpoints.
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

import schemas


class TestPatientEndpoints:
    """Tests for patient API endpoints."""

    def test_register_patient_success(self, client, sample_patient_create):
        """Test successful patient registration."""
        response = client.post(
            "/api/v1/patients/register",
            json={
                "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
                "telecom": [
                    {
                        "system": "email",
                        "value": "newpatient@example.com",
                        "use": "home",
                    }
                ],
                "gender": "male",
                "birth_date": "1990-01-15",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "patient_id" in data
        assert data["email"] == "newpatient@example.com"

    def test_register_patient_duplicate_email(self, client, sample_patient):
        """Test registering patient with duplicate email."""
        response = client.post(
            "/api/v1/patients/register",
            json={
                "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
                "telecom": [
                    {"system": "email", "value": "john.doe@example.com", "use": "home"}
                ],
                "gender": "male",
                "birth_date": "1990-01-15",
            },
        )

        assert response.status_code == 409

    def test_register_patient_no_email(self, client):
        """Test registering patient without email."""
        response = client.post(
            "/api/v1/patients/register",
            json={
                "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
                "telecom": [{"system": "phone", "value": "+1-555-0000", "use": "home"}],
                "gender": "male",
            },
        )

        assert response.status_code == 400

    def test_login_patient_success(self, client, sample_patient):
        """Test successful patient login."""
        response = client.post(
            "/api/v1/patients/login",
            json={"email": "john.doe@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["patient_id"] == sample_patient.patient_id

    def test_login_patient_not_found(self, client):
        """Test login with non-existent patient."""
        response = client.post(
            "/api/v1/patients/login",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 404

    def test_login_patient_inactive(self, client, db_session):
        """Test login with inactive patient."""
        from models import Patient
        from datetime import datetime, timezone
        import uuid

        inactive_patient_email = f"inactive-{uuid.uuid4().hex[:8]}@example.com"

        inactive_patient = Patient(
            patient_id=f"PAT-INACTIVE-{uuid.uuid4().hex[:8].upper()}",
            resource_type="Patient",
            active=False,
            name=[{"use": "official", "family": "Inactive", "given": ["Test"]}],
            telecom=[
                {"system": "email", "value": inactive_patient_email, "use": "home"}
            ],
            gender="male",
            birth_date=date(1990, 1, 1),
            meta={
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
        )
        db_session.add(inactive_patient)
        db_session.flush()

        response = client.post(
            "/api/v1/patients/login",
            json={"email": inactive_patient_email},
        )

        assert response.status_code == 403

    def test_get_patient_success(self, authenticated_client, sample_patient):
        """Test retrieving patient by ID."""
        response = authenticated_client.get(
            f"/api/v1/patients/{sample_patient.patient_id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_patient.patient_id
        assert data["resource_type"] == "Patient"

    def test_get_patient_not_found(self, authenticated_client):
        """Test retrieving non-existent patient."""
        response = authenticated_client.get(
            "/api/v1/patients/PAT-NOTFOUND",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_list_patients(self, authenticated_client, sample_patient_list):
        """Test listing patients."""
        response = authenticated_client.get(
            "/api/v1/patients/",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        assert len(data["items"]) >= 5

    def test_list_patients_pagination(self, authenticated_client, sample_patient_list):
        """Test listing patients with pagination."""
        response = authenticated_client.get(
            "/api/v1/patients/?skip=2&limit=2",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 2
        assert data["limit"] == 2
        assert len(data["items"]) == 2

    def test_update_patient(self, authenticated_client, sample_patient):
        """Test updating patient."""
        update_data = {
            "telecom": [{"system": "phone", "value": "+1-555-9999", "use": "work"}],
            "marital_status": "married",
        }

        response = authenticated_client.put(
            f"/api/v1/patients/{sample_patient.patient_id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["marital_status"] == "married"

    def test_update_patient_not_found(self, authenticated_client):
        """Test updating non-existent patient."""
        update_data = {"marital_status": "married"}

        response = authenticated_client.put(
            "/api/v1/patients/PAT-NOTFOUND",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    def test_delete_patient(self, authenticated_client, sample_patient):
        """Test deleting patient."""
        response = authenticated_client.delete(
            f"/api/v1/patients/{sample_patient.patient_id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 204

    def test_delete_patient_not_found(self, authenticated_client):
        """Test deleting non-existent patient."""
        response = authenticated_client.delete(
            "/api/v1/patients/PAT-NOTFOUND",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "patient-service"
        assert "database" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "patient-service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
