"""
Сервисный слой бизнес-логики.
"""

from datetime import date, time, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DayOfWeek, Specialization, AppointmentStatus
from app.repositories import (
    PatientRepository, DoctorRepository, ServiceRepository,
    AppointmentRepository, ScheduleRepository
)


class ScheduleService:
    """Сервис для работы с расписанием."""
    
    def __init__(self, session: AsyncSession):
        self.schedule_repo = ScheduleRepository(session)
        self.appointment_repo = AppointmentRepository(session)
        self.doctor_repo = DoctorRepository(session)
    
    async def get_available_slots(
        self,
        doctor_id: int,
        target_date: date
    ) -> List[Tuple[time, time]]:
        """
        Получить список доступных слотов для записи к врачу.
        Возвращает список кортежей (время_начала, время_окончания).
        """
        # Проверяем исключения (отпуск, больничный)
        exceptions = await self.schedule_repo.get_exceptions(doctor_id, target_date)
        for exc in exceptions:
            if exc.exception_type in ("vacation", "sick", "day_off"):
                if exc.start_time is None and exc.end_time is None:
                    # Полный выходной
                    return []
        
        # Получаем базовое расписание на день недели
        day_of_week = DayOfWeek(target_date.weekday())
        schedules = await self.schedule_repo.get_doctor_schedule(doctor_id, day_of_week)
        
        if not schedules:
            return []
        
        # Получаем существующие записи
        existing_appointments = await self.appointment_repo.get_by_doctor_and_date(
            doctor_id, 
            target_date,
            status_list=[AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
        )
        
        # Получаем перерывы
        breaks = await self.schedule_repo.get_doctor_breaks(doctor_id, day_of_week)
        
        # Генерируем слоты
        available_slots = []
        
        for schedule in schedules:
            current_time = schedule.start_time
            slot_duration = timedelta(minutes=schedule.slot_duration)
            
            while self._time_less_than(current_time, schedule.end_time):
                slot_end = self._add_minutes_to_time(current_time, schedule.slot_duration)
                
                # Проверяем, не попадает ли слот на перерыв
                if self._is_time_in_breaks(current_time, slot_end, breaks):
                    current_time = slot_end
                    continue
                
                # Проверяем, не занят ли слот существующей записью
                if not self._is_time_busy(current_time, slot_end, existing_appointments):
                    available_slots.append((current_time, slot_end))
                
                current_time = slot_end
        
        return available_slots
    
    def _time_less_than(self, t1: time, t2: time) -> bool:
        """Сравнение времени."""
        return t1.hour * 60 + t1.minute < t2.hour * 60 + t2.minute
    
    def _add_minutes_to_time(self, t: time, minutes: int) -> time:
        """Добавить минуты ко времени."""
        dt = datetime.combine(date.today(), t) + timedelta(minutes=minutes)
        return dt.time()
    
    def _is_time_in_breaks(self, start: time, end: time, breaks: List) -> bool:
        """Проверить, попадает ли время на перерыв."""
        for br in breaks:
            # Проверяем пересечение
            if not (end <= br.start_time or start >= br.end_time):
                return True
        return False
    
    def _is_time_busy(self, start: time, end: time, appointments: List) -> bool:
        """Проверить, занят ли слот."""
        for appt in appointments:
            # Проверяем пересечение
            if not (end <= appt.start_time or start >= appt.end_time):
                return True
        return False


class BookingService:
    """Сервис для записи на приём."""
    
    def __init__(self, session: AsyncSession):
        self.patient_repo = PatientRepository(session)
        self.doctor_repo = DoctorRepository(session)
        self.service_repo = ServiceRepository(session)
        self.appointment_repo = AppointmentRepository(session)
        self.schedule_service = ScheduleService(session)
    
    async def get_or_create_patient(
        self,
        telegram_id: int,
        full_name: str,
        phone: Optional[str] = None
    ):
        """Получить или создать пациента."""
        patient = await self.patient_repo.get_by_telegram_id(telegram_id)
        if not patient:
            patient = await self.patient_repo.create(
                telegram_id=telegram_id,
                full_name=full_name,
                phone=phone
            )
        return patient
    
    async def get_doctors_by_specialization(self, specialization: Specialization):
        """Получить врачей по специализации."""
        return await self.doctor_repo.get_by_specialization(specialization)
    
    async def get_services_by_specialization(self, specialization: Specialization):
        """Получить услуги для специализации."""
        return await self.service_repo.get_by_specialization(specialization)
    
    async def get_available_dates(self, doctor_id: int, days_ahead: int = 14) -> List[date]:
        """
        Получить список дат, когда у врача есть свободные слоты.
        """
        available_dates = []
        today = date.today()
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            slots = await self.schedule_service.get_available_slots(doctor_id, check_date)
            if slots:
                available_dates.append(check_date)
        
        return available_dates
    
    async def book_appointment(
        self,
        patient_id: int,
        doctor_id: int,
        service_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Создать запись на приём.
        Возвращает (успех, сообщение).
        """
        # Проверяем, свободен ли слот
        is_available = await self.appointment_repo.is_slot_available(
            doctor_id, appointment_date, start_time, end_time
        )
        
        if not is_available:
            return False, "Извините, это время уже занято. Пожалуйста, выберите другое."
        
        # Создаём запись
        appointment = await self.appointment_repo.create(
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            notes=notes
        )
        
        return True, f"Запись успешно создана! Номер записи: {appointment.id}"
    
    async def cancel_appointment(
        self,
        appointment_id: int,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Отменить запись."""
        appointment = await self.appointment_repo.cancel(appointment_id, reason)
        
        if appointment:
            return True, "Запись отменена."
        return False, "Запись не найдена."
    
    async def get_patient_appointments(
        self,
        patient_id: int,
        upcoming_only: bool = False
    ):
        """Получить записи пациента."""
        if upcoming_only:
            return await self.appointment_repo.get_upcoming_for_patient(
                patient_id, 
                date.today()
            )
        return await self.appointment_repo.get_by_patient(patient_id)