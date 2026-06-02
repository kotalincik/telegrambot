"""
Скрипт для заполнения базы данных тестовыми данными.
"""

import asyncio
from datetime import date, time, timedelta

from app.database import init_db, AsyncSessionLocal
from app.models import (
    Doctor, Service, DoctorSchedule, DoctorBreak,
    Specialization, DayOfWeek
)


async def seed_database():
    """Заполнение БД тестовыми данными."""
    async with AsyncSessionLocal() as session:
        # Создаём врачей
        doctors_data = [
            {
                "full_name": "Иванова Мария Сергеевна",
                "specialization": Specialization.THERAPIST,
                "bio": "Врач-стоматолог-терапевт с 15-летним опытом. Специализация: лечение кариеса, пульпита, периодонтита.",
            },
            {
                "full_name": "Петров Александр Викторович",
                "specialization": Specialization.SURGEON,
                "bio": "Челюстно-лицевой хирург. Удаление зубов любой сложности, имплантация.",
            },
            {
                "full_name": "Сидорова Елена Дмитриевна",
                "specialization": Specialization.ORTHODONTIST,
                "bio": "Ортодонт. Исправление прикуса, установка брекет-систем и элайнеров.",
            },
            {
                "full_name": "Козлов Дмитрий Андреевич",
                "specialization": Specialization.ORTHOPEDIST,
                "bio": "Ортопед. Протезирование, коронки, мостовидные протезы, виниры.",
            },
        ]
        
        doctors = []
        for doc_data in doctors_data:
            doctor = Doctor(**doc_data, max_patients_per_day=8)
            session.add(doctor)
            doctors.append(doctor)
        
        await session.flush()
        print(f"Создано {len(doctors)} врачей")
        
        # Создаём услуги
        services_data = [
            {
                "name": "Консультация и осмотр",
                "description": "Первичная консультация, осмотр полости рта, составление плана лечения",
                "duration_minutes": 30,
                "base_price": 1500.00,
                "required_specialization": Specialization.THERAPIST,
            },
            {
                "name": "Лечение кариеса",
                "description": "Лечение кариеса с установкой пломбы",
                "duration_minutes": 60,
                "base_price": 4500.00,
                "required_specialization": Specialization.THERAPIST,
            },
            {
                "name": "Удаление зуба простое",
                "description": "Удаление зуба без оперативного вмешательства",
                "duration_minutes": 30,
                "base_price": 3500.00,
                "required_specialization": Specialization.SURGEON,
            },
            {
                "name": "Удаление зуба сложное",
                "description": "Хирургическое удаление зуба, ретенированный зуб",
                "duration_minutes": 60,
                "base_price": 7000.00,
                "required_specialization": Specialization.SURGEON,
            },
            {
                "name": "Профессиональная чистка",
                "description": "Ультразвуковая чистка, AirFlow, полировка",
                "duration_minutes": 60,
                "base_price": 5500.00,
                "required_specialization": Specialization.THERAPIST,
            },
            {
                "name": "Коррекция брекетов",
                "description": "Плановая корректировка брекет-системы",
                "duration_minutes": 30,
                "base_price": 3000.00,
                "required_specialization": Specialization.ORTHODONTIST,
            },
            {
                "name": "Установка коронки",
                "description": "Фиксация постоянной коронки",
                "duration_minutes": 60,
                "base_price": 12000.00,
                "required_specialization": Specialization.ORTHOPEDIST,
            },
        ]
        
        services = []
        for srv_data in services_data:
            service = Service(**srv_data)
            session.add(service)
            services.append(service)
        
        await session.flush()
        print(f"Создано {len(services)} услуг")
        
        # Создаём расписание для врачей
        schedule_data = [
            # Иванова Мария (терапевт) — пн-пт, 9:00-18:00
            (doctors[0].id, [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY], time(9, 0), time(18, 0)),
            # Петров Александр (хирург) — пн-сб, 10:00-19:00
            (doctors[1].id, [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY], 
             time(10, 0), time(19, 0)),
            # Сидорова Елена (ортодонт) — пн-пт, 9:00-17:00
            (doctors[2].id, [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY], 
             time(9, 0), time(17, 0)),
            # Козлов Дмитрий (ортопед) — пн-пт, 10:00-18:00
            (doctors[3].id, [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY], 
             time(10, 0), time(18, 0)),
        ]
        
        schedules_count = 0
        for doctor_id, days, start, end in schedule_data:
            for day in days:
                schedule = DoctorSchedule(
                    doctor_id=doctor_id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    slot_duration=30,
                    is_active=True,
                    valid_from=date.today(),
                )
                session.add(schedule)
                schedules_count += 1
        
        # Добавляем перерывы на обед
        breaks_data = [
            (doctors[0].id, time(13, 0), time(14, 0), "Обед"),
            (doctors[1].id, time(14, 0), time(15, 0), "Обед"),
            (doctors[2].id, time(13, 0), time(14, 0), "Обед"),
            (doctors[3].id, time(14, 0), time(15, 0), "Обед"),
        ]
        
        for doctor_id, start, end, desc in breaks_data:
            for day in DayOfWeek:
                break_time = DoctorBreak(
                    doctor_id=doctor_id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    is_recurring=True,
                    description=desc,
                )
                session.add(break_time)
        
        await session.commit()
        print(f"Создано {schedules_count} записей расписания")
        print("Созданы перерывы на обед")
        print("\nБаза данных успешно заполнена тестовыми данными!")
        print("\nДля запуска бота выполните: python bot/main.py")
        print("Для запуска API выполните: python api/main.py")


if __name__ == "__main__":
    print("Инициализация базы данных...")
    asyncio.run(init_db())
    print("Заполнение тестовыми данными...")
    asyncio.run(seed_database())