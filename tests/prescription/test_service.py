"""
Service Layer Tests for Prescription Service.

This module tests business logic functions for prescriptions, medical records, and lab results.
"""

import os
import sys
from datetime import datetime, timezone

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
import service
from common.exceptions import ResourceNotFoundError


class TestPrescriptionIDGeneration:
    """Tests for prescription ID generation."""

    def test_generate_prescription_id_format(self):
        """Test prescription ID format."""
        prescription_id = service.generate_prescription_id()

        assert prescription_id.startswith("RX-")
        assert len(prescription_id) > 10


class TestPrescriptionService:
    """Tests for prescription service functions."""

    def test_create_prescription_success(self, test_db, sample_prescription_create):
        """Test successful prescription creation."""
        prescription = service.create_prescription(test_db, sample_prescription_create)

        assert prescription.prescription_id is not None
        assert prescription.prescription_id.startswith("RX-")
        assert prescription.patient_id == "pat-123"
        assert prescription.doctor_name == "Dr. Sarah Johnson"
        assert prescription.status == models.PrescriptionStatus.ACTIVE
        assert len(prescription.medications) == 1
        assert prescription.diagnosis == "Acute bacterial sinusitis"

    def test_get_prescription_by_id_success(self, test_db, sample_prescription):
        """Test retrieving prescription by ID."""
        prescription = service.get_prescription_by_id(
            test_db, sample_prescription.prescription_id
        )

        assert prescription.prescription_id == sample_prescription.prescription_id
        assert prescription.patient_id == sample_prescription.patient_id

    def test_get_prescription_by_id_not_found(self, test_db):
        """Test retrieving non-existent prescription."""
        with pytest.raises(ResourceNotFoundError):
            service.get_prescription_by_id(test_db, "RX-NONEXISTENT")

    def test_get_prescriptions_by_patient(self, test_db, sample_prescription):
        """Test listing prescriptions by patient."""
        prescriptions = service.get_prescriptions_by_patient(test_db, "pat-123")

        assert len(prescriptions) >= 1
        assert all(p.patient_id == "pat-123" for p in prescriptions)

    def test_get_prescriptions_by_patient_pagination(
        self, test_db, sample_prescription_create
    ):
        """Test prescription pagination."""
        for i in range(5):
            service.create_prescription(test_db, sample_prescription_create)

        page1 = service.get_prescriptions_by_patient(
            test_db, "pat-123", skip=0, limit=2
        )
        page2 = service.get_prescriptions_by_patient(
            test_db, "pat-123", skip=2, limit=2
        )

        assert len(page1) == 2
        assert len(page2) >= 2

    def test_update_prescription_success(
        self, test_db, sample_prescription, sample_prescription_update
    ):
        """Test updating prescription."""
        updated = service.update_prescription(
            test_db, sample_prescription.prescription_id, sample_prescription_update
        )

        assert updated.status == models.PrescriptionStatus.COMPLETED
        assert updated.notes == "Updated prescription notes"

    def test_update_prescription_not_found(self, test_db, sample_prescription_update):
        """Test updating non-existent prescription."""
        with pytest.raises(ResourceNotFoundError):
            service.update_prescription(
                test_db, "RX-NONEXISTENT", sample_prescription_update
            )

    def test_update_prescription_status_only(self, test_db, sample_prescription):
        """Test updating only prescription status."""
        update_data = schemas.PrescriptionUpdate(
            status=models.PrescriptionStatus.CANCELLED
        )

        updated = service.update_prescription(
            test_db, sample_prescription.prescription_id, update_data
        )

        assert updated.status == models.PrescriptionStatus.CANCELLED
        assert updated.notes == sample_prescription.notes


class TestMedicalRecordIDGeneration:
    """Tests for medical record ID generation."""

    def test_generate_record_id_format(self):
        """Test medical record ID format."""
        record_id = service.generate_record_id()

        assert record_id.startswith("REC-")
        assert len(record_id) > 10


class TestMedicalRecordService:
    """Tests for medical record service functions."""

    def test_create_medical_record_success(self, test_db, sample_medical_record_create):
        """Test successful medical record creation."""
        record = service.create_medical_record(test_db, sample_medical_record_create)

        assert record.record_id is not None
        assert record.record_id.startswith("REC-")
        assert record.patient_id == "pat-123"
        assert record.record_type == models.MedicalRecordType.CONSULTATION
        assert record.title == "Annual Physical Examination"
        assert record.vital_signs is not None

    def test_create_medical_record_without_vital_signs(self, test_db):
        """Test creating medical record without vital signs."""
        record_data = schemas.MedicalRecordCreate(
            patient_id="pat-123",
            record_type=models.MedicalRecordType.DIAGNOSIS,
            title="Diagnosis Record",
            description="Patient diagnosed with condition",
            doctor_name="Dr. Jane Doe",
        )

        record = service.create_medical_record(test_db, record_data)

        assert record.record_id is not None
        assert record.vital_signs is None

    def test_get_medical_record_by_id_success(self, test_db, sample_medical_record):
        """Test retrieving medical record by ID."""
        record = service.get_medical_record_by_id(
            test_db, sample_medical_record.record_id
        )

        assert record.record_id == sample_medical_record.record_id
        assert record.patient_id == sample_medical_record.patient_id

    def test_get_medical_record_by_id_not_found(self, test_db):
        """Test retrieving non-existent medical record."""
        with pytest.raises(ResourceNotFoundError):
            service.get_medical_record_by_id(test_db, "REC-NONEXISTENT")

    def test_get_medical_records_by_patient(self, test_db, sample_medical_record):
        """Test listing medical records by patient."""
        records = service.get_medical_records_by_patient(test_db, "pat-123")

        assert len(records) >= 1
        assert all(r.patient_id == "pat-123" for r in records)

    def test_get_medical_records_by_patient_pagination(
        self, test_db, sample_medical_record_create
    ):
        """Test medical record pagination."""
        for i in range(5):
            service.create_medical_record(test_db, sample_medical_record_create)

        page1 = service.get_medical_records_by_patient(
            test_db, "pat-123", skip=0, limit=2
        )
        page2 = service.get_medical_records_by_patient(
            test_db, "pat-123", skip=2, limit=2
        )

        assert len(page1) == 2
        assert len(page2) >= 2

    def test_update_medical_record_success(
        self, test_db, sample_medical_record, sample_medical_record_update
    ):
        """Test updating medical record."""
        updated = service.update_medical_record(
            test_db, sample_medical_record.record_id, sample_medical_record_update
        )

        assert updated.title == "Updated Medical Record Title"
        assert updated.description == "Updated description with more details"

    def test_update_medical_record_not_found(
        self, test_db, sample_medical_record_update
    ):
        """Test updating non-existent medical record."""
        with pytest.raises(ResourceNotFoundError):
            service.update_medical_record(
                test_db, "REC-NONEXISTENT", sample_medical_record_update
            )

    def test_update_medical_record_with_vital_signs(
        self, test_db, sample_medical_record, sample_vital_signs
    ):
        """Test updating medical record with vital signs."""
        update_data = schemas.MedicalRecordUpdate(vital_signs=sample_vital_signs)

        updated = service.update_medical_record(
            test_db, sample_medical_record.record_id, update_data
        )

        assert updated.vital_signs is not None
        assert updated.vital_signs.heart_rate == 72


class TestLabResultIDGeneration:
    """Tests for lab result ID generation."""

    def test_generate_lab_result_id_format(self):
        """Test lab result ID format."""
        result_id = service.generate_lab_result_id()

        assert result_id.startswith("LAB-")
        assert len(result_id) > 10


class TestLabResultService:
    """Tests for lab result service functions."""

    def test_create_lab_result_success(self, test_db, sample_lab_result_create):
        """Test successful lab result creation."""
        result = service.create_lab_result(test_db, sample_lab_result_create)

        assert result.result_id is not None
        assert result.result_id.startswith("LAB-")
        assert result.patient_id == "pat-123"
        assert result.test_panel_name == "Basic Metabolic Panel"
        assert result.status == models.LabResultStatus.PRELIMINARY
        assert len(result.tests) == 1

    def test_get_lab_result_by_id_success(self, test_db, sample_lab_result):
        """Test retrieving lab result by ID."""
        result = service.get_lab_result_by_id(test_db, sample_lab_result.result_id)

        assert result.result_id == sample_lab_result.result_id
        assert result.patient_id == sample_lab_result.patient_id

    def test_get_lab_result_by_id_not_found(self, test_db):
        """Test retrieving non-existent lab result."""
        with pytest.raises(ResourceNotFoundError):
            service.get_lab_result_by_id(test_db, "LAB-NONEXISTENT")

    def test_get_lab_results_by_patient(self, test_db, sample_lab_result):
        """Test listing lab results by patient."""
        results = service.get_lab_results_by_patient(test_db, "pat-123")

        assert len(results) >= 1
        assert all(r.patient_id == "pat-123" for r in results)

    def test_get_lab_results_by_patient_pagination(
        self, test_db, sample_lab_result_create
    ):
        """Test lab result pagination."""
        for i in range(5):
            service.create_lab_result(test_db, sample_lab_result_create)

        page1 = service.get_lab_results_by_patient(test_db, "pat-123", skip=0, limit=2)
        page2 = service.get_lab_results_by_patient(test_db, "pat-123", skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) >= 2

    def test_update_lab_result_success(
        self, test_db, sample_lab_result, sample_lab_result_update
    ):
        """Test updating lab result."""
        updated = service.update_lab_result(
            test_db, sample_lab_result.result_id, sample_lab_result_update
        )

        assert updated.status == models.LabResultStatus.FINAL
        assert updated.interpretation == "Final results confirmed - all normal"

    def test_update_lab_result_not_found(self, test_db, sample_lab_result_update):
        """Test updating non-existent lab result."""
        with pytest.raises(ResourceNotFoundError):
            service.update_lab_result(
                test_db, "LAB-NONEXISTENT", sample_lab_result_update
            )

    def test_update_lab_result_status_only(self, test_db, sample_lab_result):
        """Test updating only lab result status."""
        update_data = schemas.LabResultUpdate(status=models.LabResultStatus.FINAL)

        updated = service.update_lab_result(
            test_db, sample_lab_result.result_id, update_data
        )

        assert updated.status == models.LabResultStatus.FINAL
        assert updated.interpretation == sample_lab_result.interpretation
