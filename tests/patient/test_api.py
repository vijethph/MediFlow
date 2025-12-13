"""
API Endpoint Tests for Patient Service.

This module tests REST API endpoints.
"""

import os
import sys
from datetime import date
from unittest.mock import patch

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

    def test_login_patient_inactive(self, client, sample_patient, db_session):
        """Test login with inactive patient."""
        sample_patient.active = False
        db_session.commit()

        response = client.post(
            "/api/v1/patients/login",
            json={"email": "john.doe@example.com"},
        )

        assert response.status_code == 403

    @patch("services.patient_service.dependencies.require_authentication")
    def test_get_patient_success(self, mock_auth, client, sample_patient, mock_user):
        """Test retrieving patient by ID."""
        mock_auth.return_value = mock_user

        response = client.get(
            f"/api/v1/patients/{sample_patient.patient_id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_patient.patient_id
        assert data["resource_type"] == "Patient"

    @patch("services.patient_service.dependencies.require_authentication")
    def test_get_patient_not_found(self, mock_auth, client, mock_user):
        """Test retrieving non-existent patient."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/patients/PAT-NOTFOUND",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("services.patient_service.dependencies.require_authentication")
    def test_list_patients(self, mock_auth, client, sample_patient_list, mock_user):
        """Test listing patients."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/patients/",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        assert len(data["items"]) >= 5

    @patch("services.patient_service.dependencies.require_authentication")
    def test_list_patients_pagination(
        self, mock_auth, client, sample_patient_list, mock_user
    ):
        """Test listing patients with pagination."""
        mock_auth.return_value = mock_user

        response = client.get(
            "/api/v1/patients/?skip=2&limit=2",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 2
        assert data["limit"] == 2
        assert len(data["items"]) == 2

    @patch("services.patient_service.dependencies.require_authentication")
    def test_update_patient(self, mock_auth, client, sample_patient, mock_user):
        """Test updating patient."""
        mock_auth.return_value = mock_user

        update_data = {
            "telecom": [{"system": "phone", "value": "+1-555-9999", "use": "work"}],
            "marital_status": "married",
        }

        response = client.put(
            f"/api/v1/patients/{sample_patient.patient_id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["marital_status"] == "married"

    @patch("services.patient_service.dependencies.require_authentication")
    def test_update_patient_not_found(self, mock_auth, client, mock_user):
        """Test updating non-existent patient."""
        mock_auth.return_value = mock_user

        update_data = {"marital_status": "married"}

        response = client.put(
            "/api/v1/patients/PAT-NOTFOUND",
            json=update_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 404

    @patch("services.patient_service.dependencies.require_authentication")
    def test_delete_patient(self, mock_auth, client, sample_patient, mock_user):
        """Test deleting patient."""
        mock_auth.return_value = mock_user

        response = client.delete(
            f"/api/v1/patients/{sample_patient.patient_id}",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 204

    @patch("services.patient_service.dependencies.require_authentication")
    def test_delete_patient_not_found(self, mock_auth, client, mock_user):
        """Test deleting non-existent patient."""
        mock_auth.return_value = mock_user

        response = client.delete(
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
