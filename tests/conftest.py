"""
Фикстуры для тестирования.
"""

import asyncio
from datetime import date, time

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models import Base, Patient, Doctor, Service, Appointment, Specialization, AppointmentStatus


# Используем SQLite in-memory для тестов
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Создаёт движок БД для тестовой сессии."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Создаёт сессию БД для каждого теста."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_patient(session):
    """Создаёт тестового пациента."""
    patient = Patient(
        telegram_id=123456789,
        full_name="Иванов Иван Иванович",
        phone="+79991234567",
        birth_date=date(1990, 5, 15),
    )
    session.add(patient)
    await session.flush()
    return patient


@pytest_asyncio.fixture
async def test_doctor(session):
    """Создаёт тестового врача."""
    doctor = Doctor(
        full_name="Петров Сергей Александрович",
        specialization=Specialization.THERAPIST,
        max_patients_per_day=8,
        is_active=True,
    )
    session.add(doctor)
    await session.flush()
    return doctor


@pytest_asyncio.fixture
async def test_service(session):
    """Создаёт тестовую услугу."""
    service = Service(
        name="Осмотр и консультация",
        description="Первичный осмотр полости рта",
        duration_minutes=30,
        base_price=1500.00,
        required_specialization=Specialization.THERAPIST,
    )
    session.add(service)
    await session.flush()
    return service


@pytest_asyncio.fixture
async def test_appointment(session, test_patient, test_doctor, test_service):
    """Создаёт тестовую запись."""
    appointment = Appointment(
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        service_id=test_service.id,
        appointment_date=date(2025, 6, 15),
        start_time=time(10, 0),
        end_time=time(10, 30),
        status=AppointmentStatus.SCHEDULED,
    )
    session.add(appointment)
    await session.flush()
    return appointment