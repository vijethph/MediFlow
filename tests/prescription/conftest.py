"""
Test Configuration and Fixtures for Prescription Service.

This module provides shared fixtures for testing MongoDB-based prescription service.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "services", "prescription-service"
    ),
)

import models
import schemas
from database import get_database
from main import app


TEST_MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin:mongo_secure_password@localhost:27017/prescription_test_db?authSource=admin",
)
TEST_DATABASE_NAME = os.getenv("MONGO_DATABASE", "prescription_test_db")


@pytest.fixture(scope="session")
def mongo_client():
    """
    Create MongoDB test client.

    :return: MongoDB client
    """
    client = MongoClient(TEST_MONGO_URL)
    yield client
    client.close()


@pytest.fixture(scope="function")
def test_db(mongo_client):
    """
    Create test database instance.

    :param mongo_client: MongoDB client
    :return: Test database
    """
    db = mongo_client[TEST_DATABASE_NAME]
    yield db

    db.prescriptions.delete_many({})
    db.medical_records.delete_many({})
    db.lab_results.delete_many({})


@pytest.fixture(scope="function")
def client(test_db):
    """
    Create FastAPI test client.

    :param test_db: Test database
    :return: Test client
    """

    def override_get_db():
        return test_db

    app.dependency_overrides[get_database] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(test_db, mock_user):
    """
    Create authenticated FastAPI test client.

    Uses dependency_overrides to bypass authentication for testing.

    :param test_db: Test database
    :param mock_user: Mock user data
    :return: Authenticated test client
    """
    from dependencies import require_authentication

    def override_get_db():
        return test_db

    def override_auth():
        return mock_user

    app.dependency_overrides[get_database] = override_get_db
    app.dependency_overrides[require_authentication] = override_auth

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_token():
    """
    Create mock JWT token for testing.

    :return: Mock token string
    """
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwYXQtMTIzIiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIiwicm9sZSI6ImRvY3RvciJ9.test_signature"


@pytest.fixture
def mock_user():
    """
    Create mock user data.

    :return: Mock user dictionary
    """
    return {
        "sub": "pat-123",
        "email": "test@test.com",
        "role": "doctor",
        "token": "test_token_value",
    }


@pytest.fixture
def mock_verify(monkeypatch):
    """
    Mock verify_patient_exists function.

    :param monkeypatch: Pytest monkeypatch fixture
    :return: AsyncMock for verify_patient_exists
    """
    mock = AsyncMock(return_value=True)

    # Mock at service module level
    try:
        import service

        monkeypatch.setattr(service, "verify_patient_exists", mock)
    except (ImportError, AttributeError):
        pass

    return mock


@pytest.fixture
def sample_medication_create():
    """
    Create sample medication data.

    :return: MedicationCreate instance
    """
    return schemas.MedicationCreate(
        medication_name="Amoxicillin",
        dosage="500mg",
        frequency=models.MedicationFrequency.THREE_TIMES_DAILY,
        duration_days=7,
        instructions="Take with food",
        quantity=21,
    )


@pytest.fixture
def sample_prescription_create(sample_medication_create):
    """
    Create sample prescription creation data.

    :param sample_medication_create: Medication data
    :return: PrescriptionCreate instance
    """
    return schemas.PrescriptionCreate(
        patient_id="pat-123",
        doctor_name="Dr. Sarah Johnson",
        doctor_id="doc-456",
        appointment_id="apt-789",
        medications=[sample_medication_create],
        diagnosis="Acute bacterial sinusitis",
        notes="Patient has no known allergies",
        lab_tests_ordered=["CBC", "CMP"],
        follow_up_required=True,
        follow_up_days=14,
    )


@pytest.fixture
def sample_prescription(test_db, sample_prescription_create):
    """
    Create sample prescription in database.

    :param test_db: Test database
    :param sample_prescription_create: Prescription creation data
    :return: Created prescription
    """
    from service import create_prescription

    prescription = create_prescription(test_db, sample_prescription_create)
    return prescription


@pytest.fixture
def sample_prescription_update():
    """
    Create sample prescription update data.

    :return: PrescriptionUpdate instance
    """
    return schemas.PrescriptionUpdate(
        status=models.PrescriptionStatus.COMPLETED, notes="Updated prescription notes"
    )


@pytest.fixture
def sample_vital_signs():
    """
    Create sample vital signs data.

    :return: VitalSigns instance
    """
    return schemas.VitalSigns(
        blood_pressure_systolic=120,
        blood_pressure_diastolic=80,
        heart_rate=72,
        temperature=37.0,
        respiratory_rate=16,
        oxygen_saturation=98,
        weight_kg=70.0,
        height_cm=175.0,
    )


@pytest.fixture
def sample_medical_record_create(sample_vital_signs):
    """
    Create sample medical record creation data.

    :param sample_vital_signs: Vital signs data
    :return: MedicalRecordCreate instance
    """
    return schemas.MedicalRecordCreate(
        patient_id="pat-123",
        record_type=models.MedicalRecordType.CONSULTATION,
        title="Annual Physical Examination",
        description="Routine annual checkup - patient in good health",
        doctor_name="Dr. Sarah Johnson",
        doctor_id="doc-456",
        appointment_id="apt-789",
        vital_signs=sample_vital_signs,
        symptoms=["None reported"],
        diagnosis_codes=["Z00.00"],
    )


@pytest.fixture
def sample_medical_record(test_db, sample_medical_record_create):
    """
    Create sample medical record in database.

    :param test_db: Test database
    :param sample_medical_record_create: Medical record creation data
    :return: Created medical record
    """
    from service import create_medical_record

    record = create_medical_record(test_db, sample_medical_record_create)
    return record


@pytest.fixture
def sample_medical_record_update():
    """
    Create sample medical record update data.

    :return: MedicalRecordUpdate instance
    """
    return schemas.MedicalRecordUpdate(
        title="Updated Medical Record Title",
        description="Updated description with more details",
    )


@pytest.fixture
def sample_lab_test():
    """
    Create sample lab test data.

    :return: LabTestCreate instance
    """
    return schemas.LabTestCreate(
        test_name="Complete Blood Count",
        test_code="CBC",
        result_value="Normal",
        unit="cells/mcL",
        reference_range="4000-11000",
        abnormal_flag="N",
    )


@pytest.fixture
def sample_lab_result_create(sample_lab_test):
    """
    Create sample lab result creation data.

    :param sample_lab_test: Lab test data
    :return: LabResultCreate instance
    """
    return schemas.LabResultCreate(
        patient_id="pat-123",
        test_panel_name="Basic Metabolic Panel",
        test_category="Chemistry",
        tests=[sample_lab_test],
        ordering_doctor="Dr. Sarah Johnson",
        performing_lab="City Medical Laboratory",
        test_date=datetime.now(timezone.utc),
        result_date=datetime.now(timezone.utc),
        interpretation="All values within normal limits",
        critical_results=False,
        appointment_id="apt-789",
    )


@pytest.fixture
def sample_lab_result(test_db, sample_lab_result_create):
    """
    Create sample lab result in database.

    :param test_db: Test database
    :param sample_lab_result_create: Lab result creation data
    :return: Created lab result
    """
    from service import create_lab_result

    result = create_lab_result(test_db, sample_lab_result_create)
    return result


@pytest.fixture
def sample_lab_result_update():
    """
    Create sample lab result update data.

    :return: LabResultUpdate instance
    """
    return schemas.LabResultUpdate(
        status=models.LabResultStatus.FINAL,
        interpretation="Final results confirmed - all normal",
    )


@pytest.fixture(autouse=True)
def mock_publish_event(monkeypatch):
    """
    Mock publish_event_sync for messaging tests.

    Automatically applied to all tests to prevent RabbitMQ connection attempts.

    :param monkeypatch: Pytest monkeypatch fixture
    :return: Mock for publish_event_sync
    """
    from unittest.mock import MagicMock

    mock = MagicMock(return_value=None)

    # Mock at the service module level where it's imported
    try:
        import service

        monkeypatch.setattr(service, "publish_event_sync", mock)
    except (ImportError, AttributeError):
        pass

    # Also mock at common.messaging level as fallback
    try:
        import common.messaging

        monkeypatch.setattr(common.messaging, "publish_event_sync", mock)
    except (ImportError, AttributeError):
        pass

    return mock
