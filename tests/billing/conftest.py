"""
Test Configuration and Fixtures for Billing Service.

This module provides shared fixtures for testing.
"""

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "billing-service"),
)

import database
import models
import schemas
from common.models.shared_types import Money
from database import Base, get_db
from main import app


TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:billing_secure_password@localhost:5432/billing_test_db",
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
def sample_invoice_create():
    """
    Create sample invoice creation data.

    :return: InvoiceCreate schema
    """
    return schemas.InvoiceCreate(
        subject="pat-123",
        date=datetime.now(timezone.utc),
        line_items=[
            schemas.InvoiceLineItemCreate(
                sequence=1,
                code="CONSULT-001",
                description="General Consultation",
                quantity=Decimal("1.0"),
                unit_price=Money(value=Decimal("100.00"), currency="USD"),
                line_total=Money(value=Decimal("100.00"), currency="USD"),
            )
        ],
        payment_terms="Payment due within 30 days",
        notes="Initial consultation",
        appointment_id="appt-123",
    )


@pytest.fixture
def sample_invoice(db_session, sample_invoice_create):
    """
    Create sample invoice in database.

    :param db_session: Database session
    :param sample_invoice_create: Invoice creation data
    :return: Created invoice model
    """
    invoice = models.Invoice(
        status="draft",
        subject=sample_invoice_create.subject,
        date=sample_invoice_create.date,
        total_net_amount=Decimal("100.00"),
        total_gross_amount=Decimal("100.00"),
        total_paid_amount=Decimal("0.00"),
        total_due_amount=Decimal("100.00"),
        currency="USD",
        payment_terms=sample_invoice_create.payment_terms,
        notes=sample_invoice_create.notes,
        appointment_id=sample_invoice_create.appointment_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    # Add line item
    line_item = models.InvoiceLineItem(
        invoice_id=invoice.id,
        sequence=1,
        code="CONSULT-001",
        description="General Consultation",
        quantity=1,
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
    )
    db_session.add(line_item)
    db_session.commit()

    return invoice


@pytest.fixture
def sample_payment_create(sample_invoice):
    """
    Create sample payment creation data.

    :param sample_invoice: Sample invoice
    :return: PaymentRecordCreate schema
    """
    return schemas.PaymentRecordCreate(
        invoice_id=str(sample_invoice.id),
        amount=Money(value=Decimal("100.00"), currency="USD"),
        payment_method="credit_card",
        payment_date=datetime.now(timezone.utc),
        reference_number="PAY-001",
    )


@pytest.fixture
def sample_claim_create():
    """
    Create sample insurance claim creation data.

    :return: InsuranceClaimCreate schema
    """
    return schemas.InsuranceClaimCreate(
        claim_number="CLM-2024-001",
        type="institutional",
        patient_id="pat-123",
        provider_id="prov-123",
        insurer_name="Test Insurance Co",
        policy_number="POL-123456",
        created_date=datetime.now(timezone.utc),
        billable_period_start=datetime.now(timezone.utc),
        billable_period_end=datetime.now(timezone.utc),
        items=[
            schemas.ClaimItemCreate(
                sequence=1,
                code="CONSULT-001",
                description="General Consultation",
                quantity=Decimal("1.0"),
                unit_price=Money(value=Decimal("100.00"), currency="USD"),
                net_amount=Money(value=Decimal("100.00"), currency="USD"),
            )
        ],
    )
