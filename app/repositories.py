"""
Репозитории для работы с данными (CRUD операции).
"""

from datetime import date, time, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Patient, Doctor, Service, Appointment, 
    DoctorSchedule, DoctorBreak, ScheduleException,
    AppointmentStatus, Specialization, DayOfWeek
)


class PatientRepository:
    """Репозиторий для работы с пациентами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Patient]:
        """Получить пациента по telegram_id."""
        result = await self.session.execute(
            select(Patient).where(Patient.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """Получить пациента по ID."""
        result = await self.session.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()
    
    async def create(
        self, 
        telegram_id: int, 
        full_name: str, 
        phone: Optional[str] = None,
        birth_date: Optional[date] = None
    ) -> Patient:
        """Создать нового пацента."""
        patient = Patient(
            telegram_id=telegram_id,
            full_name=full_name,
            phone=phone,
            birth_date=birth_date,
        )
        self.session.add(patient)
        await self.session.flush()
        return patient
    
    async def update(self, patient: Patient, **kwargs) -> Patient:
        """Обновить данные пациента."""
        for key, value in kwargs.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        await self.session.flush()
        return patient
    
    async def get_all(self, active_only: bool = True) -> List[Patient]:
        """Получить список всех пациентов."""
        query = select(Patient)
        if active_only:
            query = query.where(Patient.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()


class DoctorRepository:
    """Репозиторий для работы с врачами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, doctor_id: int) -> Optional[Doctor]:
        """Получить врача по ID."""
        result = await self.session.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_specialization(self, specialization: Specialization) -> List[Doctor]:
        """Получить врачей по специализации."""
        result = await self.session.execute(
            select(Doctor)
            .where(
                and_(
                    Doctor.specialization == specialization,
                    Doctor.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def get_all(self, active_only: bool = True) -> List[Doctor]:
        """Получить всех врачей."""
        query = select(Doctor)
        if active_only:
            query = query.where(Doctor.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create(
        self,
        full_name: str,
        specialization: Specialization,
        max_patients_per_day: int = 8
    ) -> Doctor:
        """Создать нового врача."""
        doctor = Doctor(
            full_name=full_name,
            specialization=specialization,
            max_patients_per_day=max_patients_per_day,
        )
        self.session.add(doctor)
        await self.session.flush()
        return doctor


class ServiceRepository:
    """Репозиторий для работы с услугами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, service_id: int) -> Optional[Service]:
        """Получить услугу по ID."""
        result = await self.session.execute(
            select(Service).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, active_only: bool = True) -> List[Service]:
        """Получить все услуги."""
        query = select(Service)
        if active_only:
            query = query.where(Service.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_specialization(self, specialization: Specialization) -> List[Service]:
        """Получить услуги для специализации."""
        result = await self.session.execute(
            select(Service)
            .where(
                or_(
                    Service.required_specialization == specialization,
                    Service.required_specialization == None
                )
            )
            .where(Service.is_active == True)
        )
        return result.scalars().all()


class AppointmentRepository:
    """Репозиторий для работы с записями на приём."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Получить запись по ID."""
        result = await self.session.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_patient(self, patient_id: int, status: Optional[AppointmentStatus] = None) -> List[Appointment]:
        """Получить записи пациента."""
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        if status:
            query = query.where(Appointment.status == status)
        result = await self.session.execute(query.order_by(Appointment.appointment_date.desc()))
        return result.scalars().all()
    
    async def get_by_doctor_and_date(
        self, 
        doctor_id: int, 
        appointment_date: date,
        status_list: Optional[List[AppointmentStatus]] = None
    ) -> List[Appointment]:
        """Получить записи врача на конкретную дату."""
        query = select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date
            )
        )
        if status_list:
            query = query.where(Appointment.status.in_(status_list))
        
        result = await self.session.execute(
            query.order_by(Appointment.start_time)
        )
        return result.scalars().all()
    
    async def create(
        self,
        patient_id: int,
        doctor_id: int,
        service_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        notes: Optional[str] = None
    ) -> Appointment:
        """Создать новую запись."""
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
            status=AppointmentStatus.SCHEDULED
        )
        self.session.add(appointment)
        await self.session.flush()
        return appointment
    
    async def cancel(self, appointment_id: int, reason: Optional[str] = None) -> Optional[Appointment]:
        """Отменить запись."""
        appointment = await self.get_by_id(appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = datetime.now()
            appointment.cancellation_reason = reason
            await self.session.flush()
        return appointment
    
    async def confirm(self, appointment_id: int) -> Optional[Appointment]:
        """Подтвердить запись."""
        appointment = await self.get_by_id(appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_at = datetime.now()
            await self.session.flush()
        return appointment
    
    async def complete(self, appointment_id: int) -> Optional[Appointment]:
        """Отметить запись как завершённую."""
        appointment = await self.get_by_id(appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.COMPLETED
            await self.session.flush()
        return appointment
    
    async def is_slot_available(
        self,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time
    ) -> bool:
        """Проверить, свободен ли слот."""
        result = await self.session.execute(
            select(func.count(Appointment.id))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date == appointment_date,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                    or_(
                        # Пересечение интервалов
                        and_(
                            Appointment.start_time < end_time,
                            Appointment.end_time > start_time
                        )
                    )
                )
            )
        )
        count = result.scalar()
        return count == 0
    
    async def get_upcoming_for_patient(
        self, 
        patient_id: int,
        from_date: date
    ) -> List[Appointment]:
        """Получить предстоящие записи пациента."""
        result = await self.session.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.appointment_date >= from_date,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
                )
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
        )
        return result.scalars().all()


class ScheduleRepository:
    """Репозиторий для работы с расписанием."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_doctor_schedule(
        self, 
        doctor_id: int, 
        day_of_week: DayOfWeek
    ) -> List[DoctorSchedule]:
        """Получить расписание врача на день недели."""
        result = await self.session.execute(
            select(DoctorSchedule)
            .where(
                and_(
                    DoctorSchedule.doctor_id == doctor_id,
                    DoctorSchedule.day_of_week == day_of_week,
                    DoctorSchedule.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def get_doctor_breaks(
        self,
        doctor_id: int,
        day_of_week: DayOfWeek
    ) -> List[DoctorBreak]:
        """Получить перерывы врача."""
        result = await self.session.execute(
            select(DoctorBreak)
            .where(
                and_(
                    DoctorBreak.doctor_id == doctor_id,
                    or_(
                        DoctorBreak.day_of_week == day_of_week,
                        DoctorBreak.is_recurring == False
                    )
                )
            )
        )
        return result.scalars().all()
    
    async def get_exceptions(
        self,
        doctor_id: int,
        exception_date: date
    ) -> List[ScheduleException]:
        """Получить исключения в расписании врача."""
        result = await self.session.execute(
            select(ScheduleException)
            .where(
                and_(
                    ScheduleException.doctor_id == doctor_id,
                    ScheduleException.exception_date == exception_date
                )
            )
        )
        return result.scalars().all()