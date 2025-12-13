"""
Integration Tests for Prescription Service.

This module tests end-to-end workflows combining prescriptions, medical records, and lab results.
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


class TestPrescriptionWorkflow:
    """Tests for complete prescription workflows."""

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_full_prescription_lifecycle(
        self, mock_verify, client, sample_prescription_create, mock_jwt_token
    ):
        """Test complete prescription lifecycle: create, retrieve, update."""
        mock_verify.return_value = True

        # Step 1: Create prescription
        create_response = client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        prescription_id = create_data["prescription_id"]

        # Step 2: Get prescription
        get_response = client.get(
            f"/api/v1/prescriptions/{prescription_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["prescription_id"] == prescription_id
        assert get_data["status"] == "active"

        # Step 3: Update prescription
        update_response = client.put(
            f"/api/v1/prescriptions/{prescription_id}",
            json={"status": "completed", "notes": "Treatment completed"},
            headers={"Authorization": mock_jwt_token},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["status"] == "completed"

        # Step 4: Verify update
        verify_response = client.get(
            f"/api/v1/prescriptions/{prescription_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["status"] == "completed"


class TestMedicalRecordWorkflow:
    """Tests for complete medical record workflows."""

    def test_full_medical_record_lifecycle(
        self, client, sample_medical_record_create, mock_jwt_token
    ):
        """Test complete medical record lifecycle: create, retrieve, update."""
        # Step 1: Create medical record
        create_response = client.post(
            "/api/v1/medical-records",
            json=sample_medical_record_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        record_id = create_data["record_id"]

        # Step 2: Get medical record
        get_response = client.get(
            f"/api/v1/medical-records/{record_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["record_id"] == record_id

        # Step 3: Update medical record
        update_response = client.put(
            f"/api/v1/medical-records/{record_id}",
            json={
                "title": "Updated Consultation Record",
                "description": "Follow-up details added",
            },
            headers={"Authorization": mock_jwt_token},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["title"] == "Updated Consultation Record"


class TestLabResultWorkflow:
    """Tests for complete lab result workflows."""

    def test_full_lab_result_lifecycle(
        self, client, sample_lab_result_create, mock_jwt_token
    ):
        """Test complete lab result lifecycle: create, retrieve, update."""
        # Step 1: Create lab result
        create_response = client.post(
            "/api/v1/lab-results",
            json=sample_lab_result_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        result_id = create_data["result_id"]

        # Step 2: Get lab result
        get_response = client.get(
            f"/api/v1/lab-results/{result_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["result_id"] == result_id
        assert get_data["status"] == "preliminary"

        # Step 3: Update lab result to final
        update_response = client.put(
            f"/api/v1/lab-results/{result_id}",
            json={
                "status": "final",
                "interpretation": "Final results - all values normal",
            },
            headers={"Authorization": mock_jwt_token},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["status"] == "final"


class TestCombinedWorkflow:
    """Tests for workflows combining multiple resource types."""

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_prescription_with_lab_results(
        self,
        mock_verify,
        client,
        sample_prescription_create,
        sample_lab_result_create,
        mock_jwt_token,
    ):
        """Test creating prescription with associated lab results."""
        mock_verify.return_value = True

        # Step 1: Create prescription
        prescription_response = client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        assert prescription_response.status_code == 201
        prescription_data = prescription_response.json()
        prescription_id = prescription_data["prescription_id"]

        # Step 2: Create lab result linked to prescription
        lab_data = sample_lab_result_create.model_dump(mode="json")
        lab_data["prescription_id"] = prescription_id

        lab_response = client.post(
            "/api/v1/lab-results",
            json=lab_data,
            headers={"Authorization": mock_jwt_token},
        )

        assert lab_response.status_code == 201
        lab_result_data = lab_response.json()

        # Step 3: Verify prescription exists
        get_prescription = client.get(
            f"/api/v1/prescriptions/{prescription_id}",
            headers={"Authorization": mock_jwt_token},
        )

        assert get_prescription.status_code == 200

        # Step 4: Verify lab result exists
        get_lab = client.get(
            f"/api/v1/lab-results/{lab_result_data['result_id']}",
            headers={"Authorization": mock_jwt_token},
        )

        assert get_lab.status_code == 200
        assert get_lab.json()["prescription_id"] == prescription_id


class TestPatientDataRetrieval:
    """Tests for retrieving all patient data across resource types."""

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_get_all_patient_resources(
        self,
        mock_verify,
        client,
        sample_prescription_create,
        sample_medical_record_create,
        sample_lab_result_create,
        mock_jwt_token,
    ):
        """Test retrieving all resources for a patient."""
        mock_verify.return_value = True
        patient_id = "pat-123"

        # Create prescription
        client.post(
            "/api/v1/prescriptions",
            json=sample_prescription_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        # Create medical record
        client.post(
            "/api/v1/medical-records",
            json=sample_medical_record_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        # Create lab result
        client.post(
            "/api/v1/lab-results",
            json=sample_lab_result_create.model_dump(mode="json"),
            headers={"Authorization": mock_jwt_token},
        )

        # Retrieve all prescriptions
        prescriptions_response = client.get(
            f"/api/v1/prescriptions/patient/{patient_id}",
            headers={"Authorization": mock_jwt_token},
        )
        assert prescriptions_response.status_code == 200
        assert prescriptions_response.json()["total"] >= 1

        # Retrieve all medical records
        records_response = client.get(
            f"/api/v1/medical-records/patient/{patient_id}",
            headers={"Authorization": mock_jwt_token},
        )
        assert records_response.status_code == 200
        assert records_response.json()["total"] >= 1

        # Retrieve all lab results
        labs_response = client.get(
            f"/api/v1/lab-results/patient/{patient_id}",
            headers={"Authorization": mock_jwt_token},
        )
        assert labs_response.status_code == 200
        assert labs_response.json()["total"] >= 1


class TestPaginationWorkflows:
    """Tests for pagination across all resource types."""

    @patch("service.verify_patient_exists", new_callable=AsyncMock)
    def test_pagination_across_prescriptions(
        self, mock_verify, client, sample_prescription_create, mock_jwt_token
    ):
        """Test pagination for prescriptions."""
        mock_verify.return_value = True

        # Create multiple prescriptions
        for _ in range(5):
            client.post(
                "/api/v1/prescriptions",
                json=sample_prescription_create.model_dump(mode="json"),
                headers={"Authorization": mock_jwt_token},
            )

        # Get first page
        page1 = client.get(
            "/api/v1/prescriptions/patient/pat-123?skip=0&limit=2",
            headers={"Authorization": mock_jwt_token},
        )

        assert page1.status_code == 200
        page1_data = page1.json()
        assert len(page1_data["prescriptions"]) == 2

        # Get second page
        page2 = client.get(
            "/api/v1/prescriptions/patient/pat-123?skip=2&limit=2",
            headers={"Authorization": mock_jwt_token},
        )

        assert page2.status_code == 200
        page2_data = page2.json()
        assert len(page2_data["prescriptions"]) >= 2

        # Ensure different items on different pages
        page1_ids = {p["prescription_id"] for p in page1_data["prescriptions"]}
        page2_ids = {p["prescription_id"] for p in page2_data["prescriptions"]}
        assert page1_ids.isdisjoint(page2_ids)
