"""
Модели SQLAlchemy для системы записи к стоматологу.
"""

import enum
from datetime import date, time, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Numeric,
    Date,
    Time,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Boolean,
    Index,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class AppointmentStatus(str, enum.Enum):
    """Статусы записи на приём."""
    SCHEDULED = "scheduled"       # Запланировано
    CONFIRMED = "confirmed"       # Подтверждено
    COMPLETED = "completed"       # Завершено
    CANCELLED = "cancelled"       # Отменено
    NO_SHOW = "no_show"           # Неявка


class Specialization(str, enum.Enum):
    """Специализации врачей-стоматологов."""
    THERAPIST = "therapist"           # Терапевт
    ORTHOPEDIST = "orthopedist"       # Ортопед
    SURGEON = "surgeon"               # Хирург
    ORTHODONTIST = "orthodontist"     # Ортодонт
    PERIODONTIST = "periodontist"     # Пародонтолог
    ENDODONTIST = "endodontist"       # Эндодонтист
    PEDODONTIST = "pedodontist"       # Детский стоматолог
    IMPLANTOLOGIST = "implantologist" # Имплантолог


class DayOfWeek(int, enum.Enum):
    """Дни недели для расписания."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Patient(Base):
    """Модель пациента."""
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient")

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, telegram_id={self.telegram_id}, name={self.full_name})>"


class Doctor(Base):
    """Модель врача-стоматолога."""
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[Specialization] = mapped_column(Enum(Specialization), nullable=False)
    color_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # HEX цвет в календаре
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_patients_per_day: Mapped[int] = mapped_column(Integer, default=8)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor")
    doctor_services: Mapped[List["DoctorService"]] = relationship("DoctorService", back_populates="doctor")
    schedules: Mapped[List["DoctorSchedule"]] = relationship("DoctorSchedule", back_populates="doctor")
    breaks: Mapped[List["DoctorBreak"]] = relationship("DoctorBreak", back_populates="doctor")
    exceptions: Mapped[List["ScheduleException"]] = relationship("ScheduleException", back_populates="doctor")

    def __repr__(self) -> str:
        return f"<Doctor(id={self.id}, name={self.full_name}, spec={self.specialization.value})>"


class Service(Base):
    """Модель медицинской услуги."""
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)  # Длительность в минутах
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    required_specialization: Mapped[Optional[Specialization]] = mapped_column(Enum(Specialization), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="service")
    doctor_services: Mapped[List["DoctorService"]] = relationship("DoctorService", back_populates="service")

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, price={self.base_price})>"


class DoctorService(Base):
    """Связующая таблица врач-услуга с индивидуальной ценой."""
    __tablename__ = "doctor_services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    custom_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="doctor_services")
    service: Mapped["Service"] = relationship("Service", back_populates="doctor_services")

    def __repr__(self) -> str:
        return f"<DoctorService(doctor_id={self.doctor_id}, service_id={self.service_id})>"


class DoctorSchedule(Base):
    """Шаблон расписания работы врача (повторяющийся)."""
    __tablename__ = "doctor_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration: Mapped[int] = mapped_column(Integer, default=30)  # Длительность слота в минутах
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="schedules")

    __table_args__ = (
        Index('idx_doctor_schedule_day', 'doctor_id', 'day_of_week'),
    )

    def __repr__(self) -> str:
        return f"<DoctorSchedule(doctor_id={self.doctor_id}, day={self.day_of_week.name}, {self.start_time}-{self.end_time})>"


class DoctorBreak(Base):
    """Перерывы в расписании (обед и другие)."""
    __tablename__ = "doctor_breaks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[Optional[DayOfWeek]] = mapped_column(Enum(DayOfWeek), nullable=True)  # NULL = однократный
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)  # Повторяется еженедельно?
    break_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # Для разовых перерывов
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # "Обед", "Совещание" и т.д.

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="breaks")

    def __repr__(self) -> str:
        return f"<DoctorBreak(doctor_id={self.doctor_id}, {self.start_time}-{self.end_time})>"


class ScheduleException(Base):
    """Исключения в расписании (отпуск, больничный, выходной)."""
    __tablename__ = "schedule_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_type: Mapped[str] = mapped_column(String(50), nullable=False)  # vacation, sick, day_off, etc.
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)  # Для частичного дня
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="exceptions")

    __table_args__ = (
        Index('idx_doctor_exception_date', 'doctor_id', 'exception_date'),
    )

    def __repr__(self) -> str:
        return f"<ScheduleException(doctor_id={self.doctor_id}, date={self.exception_date}, type={self.exception_type})>"


class Appointment(Base):
    """Запись пациента на приём."""
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_bot: Mapped[bool] = mapped_column(Boolean, default=True)  # Через бота или администратором
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    service: Mapped["Service"] = relationship("Service", back_populates="appointments")

    __table_args__ = (
        Index('idx_appointment_date', 'appointment_date'),
        Index('idx_appointment_doctor_date', 'doctor_id', 'appointment_date'),
        Index('idx_appointment_patient', 'patient_id', 'appointment_date'),
        Index('idx_appointment_status', 'status'),
    )

    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, date={self.appointment_date}, time={self.start_time})>"

    @property
    def duration_minutes(self) -> int:
        """Вычисляет длительность приёма в минутах."""
        start = datetime.combine(self.appointment_date, self.start_time)
        end = datetime.combine(self.appointment_date, self.end_time)
        return int((end - start).total_seconds() / 60)