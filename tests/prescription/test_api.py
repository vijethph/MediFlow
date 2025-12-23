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
        self, mock_verify, authenticated_client, sample_prescription_create
    ):
        """Test creating prescription via API."""
        mock_verify.return_value = True

        response = authenticated_client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["prescription_id"].startswith("RX-")
        assert data["patient_id"] == "pat-123"
        assert data["doctor_name"] == "Dr. Sarah Johnson"

class TestMedicalRecordEndpoints:
    """Tests for medical record API endpoints."""


    def test_create_medical_record_missing_auth(
        self, client, sample_medical_record_create
    ):
        """Test creating medical record without authentication."""
        response = client.post(
            "/api/v1/medical-records",
            json=sample_medical_record_create.model_dump(mode="json"),
        )

        assert response.status_code == 401






class TestLabResultEndpoints:
    """Tests for lab result API endpoints."""


    def test_create_lab_result_missing_auth(self, client, sample_lab_result_create):
        """Test creating lab result without authentication."""
        response = client.post(
            "/api/v1/lab-results",
            json=sample_lab_result_create.model_dump(mode="json"),
        )

        assert response.status_code == 401






class TestHealthEndpoint:
    """Tests for health check endpoint."""


