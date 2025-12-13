"""
Test Configuration and Fixtures for Patient Service.

This module provides shared fixtures for testing.
"""

import os
import sys
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "patient-service"),
)

import database
import models
import schemas
from database import Base, get_db
from main import app


TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/patient_test_db"


@pytest.fixture(scope="session")
def engine():
    """
    Create test database engine.

    :return: SQLAlchemy engine
    """
    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """
    Create database session for tests.

    :param engine: Database engine
    :return: Database session
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create FastAPI test client.

    :param db_session: Database session
    :return: Test client
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_token():
    """
    Create mock JWT token for testing.

    :return: Mock token string
    """
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwYXQtMTIzIiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIn0.test_signature"


@pytest.fixture
def mock_user():
    """
    Create mock user data.

    :return: Mock user dictionary
    """
    return {
        "sub": "pat-123",
        "email": "test@test.com",
        "patient_id": "pat-123",
        "token": "mock_token",
    }


@pytest.fixture
def sample_patient_create():
    """
    Create sample patient creation data.

    :return: PatientCreate schema
    """
    return schemas.PatientCreate(
        name=[
            schemas.HumanName(
                use="official",
                family="Doe",
                given=["John", "Michael"],
            )
        ],
        telecom=[
            schemas.ContactPoint(
                system=schemas.ContactPointSystemEnum.EMAIL,
                value="john.doe@example.com",
                use="home",
            ),
            schemas.ContactPoint(
                system=schemas.ContactPointSystemEnum.PHONE,
                value="+1-555-0123",
                use="mobile",
            ),
        ],
        gender=schemas.GenderEnum.MALE,
        birth_date=date(1990, 1, 15),
        address=[
            schemas.Address(
                use="home",
                type="physical",
                line=["123 Main Street", "Apt 4B"],
                city="Boston",
                state="MA",
                postal_code="02101",
                country="USA",
            )
        ],
        marital_status="single",
    )


@pytest.fixture
def sample_patient(db_session, sample_patient_create):
    """
    Create sample patient in database.

    :param db_session: Database session
    :param sample_patient_create: Patient creation data
    :return: Created patient model
    """
    patient = models.Patient(
        patient_id="PAT-TEST123",
        resource_type="Patient",
        active=True,
        name=[n.model_dump() for n in sample_patient_create.name],
        telecom=[t.model_dump() for t in sample_patient_create.telecom],
        gender=sample_patient_create.gender.value,
        birth_date=sample_patient_create.birth_date,
        address=(
            [a.model_dump() for a in sample_patient_create.address]
            if sample_patient_create.address
            else None
        ),
        marital_status=sample_patient_create.marital_status,
        meta={
            "versionId": "1",
            "lastUpdated": datetime.utcnow().isoformat(),
        },
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    return patient


@pytest.fixture
def sample_patient_update():
    """
    Create sample patient update data.

    :return: PatientUpdate schema
    """
    return schemas.PatientUpdate(
        telecom=[
            schemas.ContactPoint(
                system=schemas.ContactPointSystemEnum.PHONE,
                value="+1-555-9999",
                use="work",
            )
        ],
        marital_status="married",
    )


@pytest.fixture
def sample_patient_create_duplicate_email():
    """
    Create patient with duplicate email for testing.

    :return: PatientCreate schema
    """
    return schemas.PatientCreate(
        name=[
            schemas.HumanName(
                use="official",
                family="Smith",
                given=["Jane"],
            )
        ],
        telecom=[
            schemas.ContactPoint(
                system=schemas.ContactPointSystemEnum.EMAIL,
                value="john.doe@example.com",
                use="home",
            )
        ],
        gender=schemas.GenderEnum.FEMALE,
        birth_date=date(1985, 5, 20),
    )


@pytest.fixture
def sample_patient_list(db_session):
    """
    Create multiple sample patients in database.

    :param db_session: Database session
    :return: List of created patient models
    """
    patients = []
    for i in range(5):
        patient = models.Patient(
            patient_id=f"PAT-TEST{i:03d}",
            resource_type="Patient",
            active=True,
            name=[
                {
                    "use": "official",
                    "family": f"Patient{i}",
                    "given": [f"Test{i}"],
                }
            ],
            telecom=[
                {
                    "system": "email",
                    "value": f"patient{i}@example.com",
                    "use": "home",
                }
            ],
            gender="male" if i % 2 == 0 else "female",
            birth_date=date(1990 + i, 1, 1),
            meta={
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat(),
            },
        )
        db_session.add(patient)
        patients.append(patient)

    db_session.commit()
    for patient in patients:
        db_session.refresh(patient)

    return patients
