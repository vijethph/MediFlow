"""
Service Layer Tests for Patient Service.

This module tests business logic functions.
"""

import os
import sys
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "patient-service"),
)

import schemas
import service
from common.exceptions import (
    DuplicateResourceError,
    PatientNotFoundError,
    ValidationError,
)


class TestPatientService:
    """Tests for patient service functions."""

    def test_generate_patient_id(self):
        """Test patient ID generation."""
        patient_id = service.generate_patient_id()

        assert patient_id.startswith("PAT-")
        assert len(patient_id) == 12

    def test_create_patient_success(self, db_session, sample_patient_create):
        """Test successful patient creation."""
        patient = service.create_patient(db_session, sample_patient_create)

        assert patient.id is not None
        assert patient.patient_id.startswith("PAT-")
        assert patient.resource_type == "Patient"
        assert patient.active is True
        assert patient.name[0]["family"] == "Doe"
        assert patient.gender == "male"

    def test_create_patient_duplicate_email(
        self, db_session, sample_patient, sample_patient_create_duplicate_email
    ):
        """Test creating patient with duplicate email."""
        with pytest.raises(DuplicateResourceError):
            service.create_patient(db_session, sample_patient_create_duplicate_email)

    def test_get_patient_by_id_success(self, db_session, sample_patient):
        """Test retrieving patient by ID."""
        patient = service.get_patient_by_id(db_session, sample_patient.patient_id)

        assert patient.id == sample_patient.id
        assert patient.patient_id == sample_patient.patient_id

    def test_get_patient_by_id_not_found(self, db_session):
        """Test retrieving non-existent patient."""
        with pytest.raises(PatientNotFoundError):
            service.get_patient_by_id(db_session, "PAT-NOTFOUND")

    def test_get_patient_by_email_success(self, db_session, sample_patient):
        """Test retrieving patient by email."""
        patient_email = sample_patient.telecom[0]["value"]
        patient = service.get_patient_by_email(db_session, patient_email)

        assert patient is not None
        assert patient.id == sample_patient.id

    def test_get_patient_by_email_not_found(self, db_session):
        """Test retrieving patient by non-existent email."""
        patient = service.get_patient_by_email(db_session, "nonexistent@example.com")

        assert patient is None

    def test_get_patients_pagination(self, db_session, sample_patient_list):
        """Test listing patients with pagination."""
        patients, total = service.get_patients(db_session, skip=0, limit=3)

        assert len(patients) == 3
        assert total >= 5

    def test_get_patients_skip(self, db_session, sample_patient_list):
        """Test listing patients with skip."""
        patients, total = service.get_patients(db_session, skip=2, limit=10)

        assert len(patients) >= 3
        assert total >= 5

    def test_update_patient_success(
        self, db_session, sample_patient, sample_patient_update
    ):
        """Test updating patient."""
        updated_patient = service.update_patient(
            db_session, sample_patient.patient_id, sample_patient_update
        )

        assert updated_patient.marital_status == "married"
        assert updated_patient.telecom[0]["value"] == "+1-555-9999"
        assert int(updated_patient.meta.get("versionId", "1")) == 2

    def test_update_patient_not_found(self, db_session, sample_patient_update):
        """Test updating non-existent patient."""
        with pytest.raises(PatientNotFoundError):
            service.update_patient(db_session, "PAT-NOTFOUND", sample_patient_update)

    def test_update_patient_no_changes(self, db_session, sample_patient):
        """Test updating patient with no changes."""
        empty_update = schemas.PatientUpdate()
        updated_patient = service.update_patient(
            db_session, sample_patient.patient_id, empty_update
        )

        assert updated_patient.id == sample_patient.id

    def test_delete_patient_success(self, db_session, sample_patient):
        """Test soft deleting patient."""
        result = service.delete_patient(db_session, sample_patient.patient_id)

        assert result is True

        db_session.refresh(sample_patient)
        assert sample_patient.active is False

    def test_delete_patient_not_found(self, db_session):
        """Test deleting non-existent patient."""
        with pytest.raises(PatientNotFoundError):
            service.delete_patient(db_session, "PAT-NOTFOUND")

    def test_count_active_patients(self, db_session, sample_patient_list):
        """Test counting active patients."""
        count = service.count_active_patients(db_session)

        assert count >= 5

    def test_authenticate_patient_success(self, db_session, sample_patient):
        """Test successful patient authentication."""
        patient_email = sample_patient.telecom[0]["value"]
        patient, token = service.authenticate_patient(db_session, patient_email)

        assert patient.id == sample_patient.id
        assert token is not None
        assert isinstance(token, str)

    def test_authenticate_patient_not_found(self, db_session):
        """Test authenticating non-existent patient."""
        with pytest.raises(PatientNotFoundError):
            service.authenticate_patient(db_session, "nonexistent@example.com")

    def test_authenticate_patient_inactive(self, db_session):
        """Test authenticating inactive patient."""
        from models import Patient
        from datetime import date, datetime, timezone
        import uuid

        inactive_email = f"inactive-{uuid.uuid4().hex[:8]}@example.com"
        inactive_patient = Patient(
            patient_id=f"PAT-INACTIVE-{uuid.uuid4().hex[:8].upper()}",
            resource_type="Patient",
            active=False,
            name=[{"use": "official", "family": "Inactive", "given": ["Test"]}],
            telecom=[{"system": "email", "value": inactive_email, "use": "home"}],
            gender="male",
            birth_date=date(1990, 1, 1),
            meta={
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
        )
        db_session.add(inactive_patient)
        db_session.flush()

        with pytest.raises(ValidationError):
            service.authenticate_patient(db_session, inactive_email)

    def test_create_access_token(self):
        """Test JWT access token creation."""
        data = {"patient_id": "pat-123", "email": "test@example.com"}
        expires_delta = timedelta(minutes=30)

        token = service.create_access_token(data, expires_delta)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
