"""
Тесты для репозиториев (CRUD операции).
"""

import pytest
from datetime import date, time

from app.repositories import (
    PatientRepository, DoctorRepository, ServiceRepository,
    AppointmentRepository
)
from app.models import Specialization, AppointmentStatus


@pytest.mark.asyncio
async def test_create_patient(session):
    """Тест создания пациента."""
    repo = PatientRepository(session)
    
    patient = await repo.create(
        telegram_id=12345,
        full_name="Тестовый Пациент",
        phone="+79998887766",
        birth_date=date(1995, 3, 10)
    )
    
    assert patient.id is not None
    assert patient.telegram_id == 12345
    assert patient.full_name == "Тестовый Пациент"


@pytest.mark.asyncio
async def test_get_patient_by_telegram_id(session, test_patient):
    """Тест получения пациента по telegram_id."""
    repo = PatientRepository(session)
    
    patient = await repo.get_by_telegram_id(123456789)
    
    assert patient is not None
    assert patient.full_name == "Иванов Иван Иванович"


@pytest.mark.asyncio
async def test_get_patient_by_id(session, test_patient):
    """Тест получения пациента по ID."""
    repo = PatientRepository(session)
    
    patient = await repo.get_by_id(test_patient.id)
    
    assert patient is not None
    assert patient.telegram_id == 123456789


@pytest.mark.asyncio
async def test_create_doctor(session):
    """Тест создания врача."""
    repo = DoctorRepository(session)
    
    doctor = await repo.create(
        full_name="Сидоров Андрей Петрович",
        specialization=Specialization.SURGEON,
        max_patients_per_day=6
    )
    
    assert doctor.id is not None
    assert doctor.specialization == Specialization.SURGEON
    assert doctor.is_active is True


@pytest.mark.asyncio
async def test_get_doctors_by_specialization(session, test_doctor):
    """Тест получения врачей по специализации."""
    repo = DoctorRepository(session)
    
    doctors = await repo.get_by_specialization(Specialization.THERAPIST)
    
    assert len(doctors) >= 1
    assert any(d.full_name == "Петров Сергей Александрович" for d in doctors)


@pytest.mark.asyncio
async def test_get_service_by_id(session, test_service):
    """Тест получения услуги по ID."""
    repo = ServiceRepository(session)
    
    service = await repo.get_by_id(test_service.id)
    
    assert service is not None
    assert service.name == "Осмотр и консультация"
    assert service.base_price == 1500.00


@pytest.mark.asyncio
async def test_create_appointment(session, test_patient, test_doctor, test_service):
    """Тест создания записи на приём."""
    repo = AppointmentRepository(session)
    
    appointment = await repo.create(
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        service_id=test_service.id,
        appointment_date=date(2025, 6, 20),
        start_time=time(14, 0),
        end_time=time(14, 30),
        notes="Тестовая запись"
    )
    
    assert appointment.id is not None
    assert appointment.status == AppointmentStatus.SCHEDULED
    assert appointment.patient_id == test_patient.id


@pytest.mark.asyncio
async def test_cancel_appointment(session, test_appointment):
    """Тест отмены записи."""
    repo = AppointmentRepository(session)
    
    cancelled = await repo.cancel(test_appointment.id, "По просьбе пациента")
    
    assert cancelled is not None
    assert cancelled.status == AppointmentStatus.CANCELLED
    assert cancelled.cancellation_reason == "По просьбе пациента"


@pytest.mark.asyncio
async def test_confirm_appointment(session, test_appointment):
    """Тест подтверждения записи."""
    repo = AppointmentRepository(session)
    
    confirmed = await repo.confirm(test_appointment.id)
    
    assert confirmed is not None
    assert confirmed.status == AppointmentStatus.CONFIRMED
    assert confirmed.confirmed_at is not None


@pytest.mark.asyncio
async def test_get_appointments_by_patient(session, test_patient, test_appointment):
    """Тест получения записей пациента."""
    repo = AppointmentRepository(session)
    
    appointments = await repo.get_by_patient(test_patient.id)
    
    assert len(appointments) >= 1
    assert any(a.id == test_appointment.id for a in appointments)


@pytest.mark.asyncio
async def test_is_slot_available_true(session, test_doctor, test_service):
    """Тест проверки свободного слота (должен быть свободен)."""
    repo = AppointmentRepository(session)
    
    is_available = await repo.is_slot_available(
        doctor_id=test_doctor.id,
        appointment_date=date(2030, 1, 1),  # Дата в далёком будущем
        start_time=time(9, 0),
        end_time=time(9, 30)
    )
    
    assert is_available is True


@pytest.mark.asyncio
async def test_is_slot_available_false(session, test_doctor, test_appointment):
    """Тест проверки занятого слота (должен быть занят)."""
    repo = AppointmentRepository(session)
    
    # Проверяем на ту же дату и время, что и test_appointment
    is_available = await repo.is_slot_available(
        doctor_id=test_doctor.id,
        appointment_date=test_appointment.appointment_date,
        start_time=test_appointment.start_time,
        end_time=test_appointment.end_time
    )
    
    assert is_available is False