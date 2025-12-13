"""
API Endpoint Tests for Prescription Service.

This module tests REST API endpoints for prescriptions, medical records, and lab results.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "services", "prescription-service"
    ),
)

import models
import schemas


class TestPrescriptionEndpoints:
    """Tests for prescription API endpoints."""

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_create_prescription_success(
        self, mock_verify, client, sample_prescription_create, mock_jwt_token
    ):
        """Test creating prescription via API."""
        mock_verify.return_value = True

        response = client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["prescription_id"].startswith("RX-")
        assert data["patient_id"] == "pat-123"
        assert data["doctor_name"] == "Dr. Sarah Johnson"

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_create_prescription_patient_not_found(
        self, mock_verify, client, sample_prescription_create, mock_jwt_token
    ):
        """Test creating prescription with non-existent patient."""
        from common.exceptions import PatientNotFoundError

        mock_verify.side_effect = PatientNotFoundError("pat-999")

        response = client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404

    def test_create_prescription_missing_auth(self, client, sample_prescription_create):
        """Test creating prescription without authentication."""
        response = client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
        )

        assert response.status_code == 403

    def test_get_prescription_success(
        self, client, sample_prescription, mock_jwt_token
    ):
        """Test retrieving prescription by ID."""
        response = client.get(
            f"/api/v1/prescriptions/{sample_prescription.prescription_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["prescription_id"] == sample_prescription.prescription_id

    def test_get_prescription_not_found(self, client, mock_jwt_token):
        """Test retrieving non-existent prescription."""
        response = client.get(
            "/api/v1/prescriptions/RX-NONEXISTENT",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404

    def test_get_prescriptions_by_patient_success(
        self, client, sample_prescription, mock_jwt_token
    ):
        """Test listing prescriptions by patient."""
        response = client.get(
            "/api/v1/prescriptions/patient/pat-123",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "prescriptions" in data
        assert data["total"] >= 1

    def test_get_prescriptions_by_patient_pagination(
        self, client, sample_prescription, mock_jwt_token
    ):
        """Test prescription pagination."""
        response = client.get(
            "/api/v1/prescriptions/patient/pat-123?skip=0&limit=10",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["prescriptions"]) >= 1

    def test_update_prescription_success(
        self, client, sample_prescription, sample_prescription_update, mock_jwt_token
    ):
        """Test updating prescription."""
        response = client.put(
            f"/api/v1/prescriptions/{sample_prescription.prescription_id}",
            json=sample_prescription_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_update_prescription_not_found(
        self, client, sample_prescription_update, mock_jwt_token
    ):
        """Test updating non-existent prescription."""
        response = client.put(
            "/api/v1/prescriptions/RX-NONEXISTENT",
            json=sample_prescription_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404


class TestMedicalRecordEndpoints:
    """Tests for medical record API endpoints."""

    def test_create_medical_record_success(
        self, client, sample_medical_record_create, mock_jwt_token
    ):
        """Test creating medical record via API."""
        response = client.post(
            "/api/v1/medical-records",
            json=sample_medical_record_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["record_id"].startswith("REC-")
        assert data["patient_id"] == "pat-123"

    def test_create_medical_record_missing_auth(
        self, client, sample_medical_record_create
    ):
        """Test creating medical record without authentication."""
        response = client.post(
            "/api/v1/medical-records",
            json=sample_medical_record_create.model_dump(mode="json"),
        )

        assert response.status_code == 403

    def test_get_medical_record_success(
        self, client, sample_medical_record, mock_jwt_token
    ):
        """Test retrieving medical record by ID."""
        response = client.get(
            f"/api/v1/medical-records/{sample_medical_record.record_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == sample_medical_record.record_id

    def test_get_medical_record_not_found(self, client, mock_jwt_token):
        """Test retrieving non-existent medical record."""
        response = client.get(
            "/api/v1/medical-records/REC-NONEXISTENT",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404

    def test_get_medical_records_by_patient_success(
        self, client, sample_medical_record, mock_jwt_token
    ):
        """Test listing medical records by patient."""
        response = client.get(
            "/api/v1/medical-records/patient/pat-123",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "records" in data
        assert data["total"] >= 1

    def test_update_medical_record_success(
        self,
        client,
        sample_medical_record,
        sample_medical_record_update,
        mock_jwt_token,
    ):
        """Test updating medical record."""
        response = client.put(
            f"/api/v1/medical-records/{sample_medical_record.record_id}",
            json=sample_medical_record_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Medical Record Title"

    def test_update_medical_record_not_found(
        self, client, sample_medical_record_update, mock_jwt_token
    ):
        """Test updating non-existent medical record."""
        response = client.put(
            "/api/v1/medical-records/REC-NONEXISTENT",
            json=sample_medical_record_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404


class TestLabResultEndpoints:
    """Tests for lab result API endpoints."""

    def test_create_lab_result_success(
        self, client, sample_lab_result_create, mock_jwt_token
    ):
        """Test creating lab result via API."""
        response = client.post(
            "/api/v1/lab-results",
            json=sample_lab_result_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["result_id"].startswith("LAB-")
        assert data["patient_id"] == "pat-123"

    def test_create_lab_result_missing_auth(self, client, sample_lab_result_create):
        """Test creating lab result without authentication."""
        response = client.post(
            "/api/v1/lab-results",
            json=sample_lab_result_create.model_dump(mode="json"),
        )

        assert response.status_code == 403

    def test_get_lab_result_success(self, client, sample_lab_result, mock_jwt_token):
        """Test retrieving lab result by ID."""
        response = client.get(
            f"/api/v1/lab-results/{sample_lab_result.result_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result_id"] == sample_lab_result.result_id

    def test_get_lab_result_not_found(self, client, mock_jwt_token):
        """Test retrieving non-existent lab result."""
        response = client.get(
            "/api/v1/lab-results/LAB-NONEXISTENT",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404

    def test_get_lab_results_by_patient_success(
        self, client, sample_lab_result, mock_jwt_token
    ):
        """Test listing lab results by patient."""
        response = client.get(
            "/api/v1/lab-results/patient/pat-123",
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "results" in data
        assert data["total"] >= 1

    def test_update_lab_result_success(
        self, client, sample_lab_result, sample_lab_result_update, mock_jwt_token
    ):
        """Test updating lab result."""
        response = client.put(
            f"/api/v1/lab-results/{sample_lab_result.result_id}",
            json=sample_lab_result_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "final"

    def test_update_lab_result_not_found(
        self, client, sample_lab_result_update, mock_jwt_token
    ):
        """Test updating non-existent lab result."""
        response = client.put(
            "/api/v1/lab-results/LAB-NONEXISTENT",
            json=sample_lab_result_update.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert response.status_code == 404


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "Prescription Service"
