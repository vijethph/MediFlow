"""
Service Layer Tests for Appointment Service.

This module tests business logic functions.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "services", "appointment-service"
    ),
)

import schemas
import service
from common.exceptions import AppointmentNotFoundError


class TestAppointmentService:
    """Tests for appointment service functions."""

    def test_create_appointment_success(self, db_session, sample_appointment_create):
        """Test successful appointment creation."""
        appointment = service.create_appointment(db_session, sample_appointment_create)

        assert appointment.id is not None
        assert appointment.status == "booked"
        assert appointment.description == "Annual checkup"
        assert appointment.specialty == "General Medicine"
        assert appointment.location == "Room 101"
        assert appointment.minute_duration == 60
        assert len(appointment.participant) == 2

    def test_create_appointment_without_practitioner(
        self, db_session, sample_appointment_create
    ):
        """Test creating appointment without practitioner."""
        sample_appointment_create.practitioner_id = None
        sample_appointment_create.practitioner_name = None

        appointment = service.create_appointment(db_session, sample_appointment_create)

        assert appointment.id is not None
        assert len(appointment.participant) == 1
        assert appointment.participant[0]["type"] == ["patient"]

    def test_create_appointment_auto_calculate_duration(
        self, db_session, sample_appointment_create
    ):
        """Test appointment duration auto-calculation."""
        sample_appointment_create.minute_duration = None

        appointment = service.create_appointment(db_session, sample_appointment_create)

        assert appointment.minute_duration == 60

    def test_get_appointment_by_id_success(self, db_session, sample_appointment):
        """Test retrieving appointment by ID."""
        appointment = service.get_appointment_by_id(
            db_session, str(sample_appointment.id)
        )

        assert appointment.id == sample_appointment.id
        assert appointment.status == sample_appointment.status

    def test_get_appointment_by_id_not_found(self, db_session):
        """Test retrieving non-existent appointment."""
        with pytest.raises(AppointmentNotFoundError):
            service.get_appointment_by_id(
                db_session, "00000000-0000-0000-0000-000000000000"
            )

    def test_list_appointments_all(self, db_session, sample_appointment):
        """Test listing all appointments."""
        appointments, total = service.list_appointments(db_session)

        assert total >= 1
        assert len(appointments) >= 1

    def test_list_appointments_by_patient(self, db_session, sample_appointment):
        """Test listing appointments by patient ID."""
        appointments, total = service.list_appointments(
            db_session, patient_id="pat-123"
        )

        assert total >= 1
        assert all(
            any(p["actor"] == "pat-123" for p in apt.participant)
            for apt in appointments
        )

    def test_list_appointments_by_practitioner(self, db_session, sample_appointment):
        """Test listing appointments by practitioner ID."""
        appointments, total = service.list_appointments(
            db_session, practitioner_id="prac-456"
        )

        assert total >= 1
        assert all(
            any(p["actor"] == "prac-456" for p in apt.participant)
            for apt in appointments
        )

    def test_list_appointments_by_status(self, db_session, sample_appointment):
        """Test listing appointments by status."""
        appointments, total = service.list_appointments(db_session, status="booked")

        assert total >= 1
        assert all(apt.status == "booked" for apt in appointments)

    def test_list_appointments_by_date_range(self, db_session, sample_appointment):
        """Test listing appointments by date range."""
        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=30)

        appointments, total = service.list_appointments(
            db_session, start_date=start_date, end_date=end_date
        )

        assert total >= 1
        assert all(start_date <= apt.start <= end_date for apt in appointments)

    def test_list_appointments_with_pagination(self, db_session, sample_appointment):
        """Test appointment list pagination."""
        appointments, total = service.list_appointments(db_session, skip=0, limit=5)

        assert len(appointments) <= 5
        assert total >= 0

    def test_update_appointment_success(self, db_session, sample_appointment):
        """Test updating appointment."""
        update_data = schemas.AppointmentUpdate(
            status=schemas.AppointmentStatusEnum.FULFILLED,
            comment="Patient arrived on time",
        )

        updated_appointment = service.update_appointment(
            db_session, str(sample_appointment.id), update_data
        )

        assert updated_appointment.status == "fulfilled"
        assert updated_appointment.comment == "Patient arrived on time"

    def test_update_appointment_not_found(self, db_session):
        """Test updating non-existent appointment."""
        update_data = schemas.AppointmentUpdate(
            status=schemas.AppointmentStatusEnum.FULFILLED
        )

        with pytest.raises(AppointmentNotFoundError):
            service.update_appointment(
                db_session, "00000000-0000-0000-0000-000000000000", update_data
            )

    def test_delete_appointment_success(self, db_session, sample_appointment):
        """Test deleting appointment."""
        appointment_id = str(sample_appointment.id)

        service.delete_appointment(db_session, appointment_id)

        with pytest.raises(AppointmentNotFoundError):
            service.get_appointment_by_id(db_session, appointment_id)

    def test_delete_appointment_not_found(self, db_session):
        """Test deleting non-existent appointment."""
        with pytest.raises(AppointmentNotFoundError):
            service.delete_appointment(
                db_session, "00000000-0000-0000-0000-000000000000"
            )

    def test_cancel_appointment_success(self, db_session, sample_appointment):
        """Test cancelling appointment."""
        cancelled_appointment = service.cancel_appointment(
            db_session, str(sample_appointment.id)
        )

        assert cancelled_appointment.status == "cancelled"
        assert cancelled_appointment.id == sample_appointment.id

    def test_cancel_appointment_not_found(self, db_session):
        """Test cancelling non-existent appointment."""
        with pytest.raises(AppointmentNotFoundError):
            service.cancel_appointment(
                db_session, "00000000-0000-0000-0000-000000000000"
            )

    def test_appointment_participant_structure(self, db_session, sample_appointment):
        """Test appointment participant JSONB structure."""
        appointment = service.get_appointment_by_id(
            db_session, str(sample_appointment.id)
        )

        assert isinstance(appointment.participant, list)
        assert len(appointment.participant) >= 1

        for participant in appointment.participant:
            assert "type" in participant
            assert "actor" in participant
            assert "status" in participant
