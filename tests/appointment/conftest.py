"""
Test Configuration and Fixtures for Appointment Service.

This module provides shared fixtures for testing.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "services", "appointment-service"
    ),
)

import database
import models
import schemas
from database import Base, get_db
from main import app


TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:appointment_secure_password@localhost:5434/appointment_test_db",
)


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


@pytest.fixture(scope="function", autouse=True)
def mock_publish_event():
    """
    Mock async publish_event to prevent runtime warnings in sync tests.

    :return: Mock publish_event function
    """
    from unittest.mock import patch

    def mock_sync_publish(*args, **kwargs):
        return None

    with patch(
        "common.messaging.publish_event_sync", side_effect=mock_sync_publish
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def db_session(engine):
    """
    Create database session for tests with transaction rollback for isolation.

    :param engine: Database engine
    :return: Database session
    """
    connection = engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = testing_session_local()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


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


@pytest.fixture(scope="function")
def authenticated_client(db_session, mock_user):
    """
    Create FastAPI test client with mocked authentication.

    :param db_session: Database session
    :param mock_user: Mock user data
    :return: Test client with authentication
    """
    from dependencies import require_authentication

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
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
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSIsInJvbGUiOiJkb2N0b3IifQ.test_signature"


@pytest.fixture
def mock_user():
    """
    Create mock user data.

    :return: Mock user dictionary
    """
    return {
        "sub": "user-123",
        "email": "test@test.com",
        "role": "doctor",
        "patient_id": "pat-123",
        "token": "mock_token",
    }


@pytest.fixture
def sample_appointment_create():
    """
    Create sample appointment creation data.

    :return: AppointmentCreate schema
    """
    start_time = datetime.now() + timedelta(days=7)
    end_time = start_time + timedelta(hours=1)

    return schemas.AppointmentCreate(
        status=schemas.AppointmentStatusEnum.BOOKED,
        start=start_time,
        end=end_time,
        patient_id="pat-123",
        practitioner_name="Dr. Jane Doe",
        practitioner_id="prac-456",
        description="Annual checkup",
        specialty="General Medicine",
        location="Room 101",
        minute_duration=60,
    )


@pytest.fixture
def sample_appointment(db_session, sample_appointment_create):
    """
    Create sample appointment in database.

    :param db_session: Database session
    :param sample_appointment_create: Appointment creation data
    :return: Created appointment model
    """
    participant_data = [
        {
            "type": ["patient"],
            "actor": sample_appointment_create.patient_id,
            "required": "required",
            "status": "accepted",
        },
        {
            "type": ["practitioner"],
            "actor": sample_appointment_create.practitioner_id,
            "required": "required",
            "status": "accepted",
        },
    ]

    appointment = models.Appointment(
        status=sample_appointment_create.status.value,
        start=sample_appointment_create.start,
        end=sample_appointment_create.end,
        description=sample_appointment_create.description,
        specialty=sample_appointment_create.specialty,
        location=sample_appointment_create.location,
        minute_duration=sample_appointment_create.minute_duration,
        participant=participant_data,
        resource_type="Appointment",
    )

    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)

    return appointment


@pytest.fixture
def sample_appointment_update():
    """
    Create sample appointment update data.

    :return: AppointmentUpdate schema
    """
    return schemas.AppointmentUpdate(
        status=schemas.AppointmentStatusEnum.FULFILLED,
        comment="Patient arrived on time",
        description="Completed annual checkup",
    )
