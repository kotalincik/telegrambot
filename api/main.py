"""
FastAPI приложение для админ-панели и API системы записи.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, init_db, close_db
from app.models import AppointmentStatus, Specialization
from app.services import BookingService, ScheduleService
from api.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для старта/остановки приложения."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Dental Booking API",
    description="API для системы записи к стоматологу",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем дашборд
app.include_router(dashboard_router)


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "service": "Dental Booking API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса."""
    return {"status": "ok"}


# ======== API для врачей ========

@app.get("/api/doctors")
async def get_doctors(specialization: Specialization = None, session: AsyncSession = Depends(get_db)):
    """Получить список врачей."""
    from app.repositories import DoctorRepository
    repo = DoctorRepository(session)
    
    if specialization:
        doctors = await repo.get_by_specialization(specialization)
    else:
        doctors = await repo.get_all()
    
    return [
        {
            "id": d.id,
            "full_name": d.full_name,
            "specialization": d.specialization.value,
            "max_patients_per_day": d.max_patients_per_day,
            "is_active": d.is_active,
        }
        for d in doctors
    ]


@app.get("/api/doctors/{doctor_id}/schedule")
async def get_doctor_schedule(
    doctor_id: int,
    date: str,
    session: AsyncSession = Depends(get_db)
):
    """Получить расписание врача на дату."""
    from datetime import datetime
    
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    schedule_service = ScheduleService(session)
    slots = await schedule_service.get_available_slots(doctor_id, target_date)
    
    return {
        "doctor_id": doctor_id,
        "date": date,
        "available_slots": [
            {
                "start_time": start.strftime("%H:%M"),
                "end_time": end.strftime("%H:%M")
            }
            for start, end in slots
        ]
    }


# ======== API для записей ========

@app.get("/api/appointments")
async def get_appointments(
    patient_id: int = None,
    doctor_id: int = None,
    date_from: str = None,
    date_to: str = None,
    status: AppointmentStatus = None,
    session: AsyncSession = Depends(get_db)
):
    """Получить список записей с фильтрацией."""
    from app.repositories import AppointmentRepository
    from sqlalchemy import select, and_
    from datetime import datetime
    from app.models import Appointment
    
    repo = AppointmentRepository(session)
    
    # Базовый запрос
    query = select(Appointment)
    
    conditions = []
    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)
    if doctor_id:
        conditions.append(Appointment.doctor_id == doctor_id)
    if date_from:
        conditions.append(Appointment.appointment_date >= datetime.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        conditions.append(Appointment.appointment_date <= datetime.strptime(date_to, "%Y-%m-%d").date())
    if status:
        conditions.append(Appointment.status == status)
    
    # Выполняем запрос
    from sqlalchemy.ext.asyncio import AsyncSession
    result = await session.execute(query.where(and_(*conditions) if conditions else True).order_by(Appointment.appointment_date.desc()))
    appointments = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": a.patient.full_name,
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.full_name,
            "service_id": a.service_id,
            "service_name": a.service.name,
            "date": a.appointment_date.isoformat(),
            "start_time": a.start_time.isoformat(),
            "end_time": a.end_time.isoformat(),
            "status": a.status.value,
            "price": float(a.service.base_price),
        }
        for a in appointments
    ]


@app.post("/api/appointments/{appointment_id}/cancel")
async def cancel_appointment_api(
    appointment_id: int,
    reason: str = None,
    session: AsyncSession = Depends(get_db)
):
    """Отменить запись через API."""
    booking_service = BookingService(session)
    success, message = await booking_service.cancel_appointment(appointment_id, reason)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"success": True, "message": message}


@app.post("/api/appointments/{appointment_id}/confirm")
async def confirm_appointment_api(
    appointment_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Подтвердить запись через API."""
    from app.repositories import AppointmentRepository
    repo = AppointmentRepository(session)
    appointment = await repo.confirm(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    return {"success": True, "appointment_id": appointment_id, "status": "confirmed"}


# ======== API для статистики ========

@app.get("/api/statistics")
async def get_statistics(session: AsyncSession = Depends(get_db)):
    """Получить статистику клиники."""
    from sqlalchemy import func, select
    from datetime import date
    from app.models import Appointment, Doctor, Patient, Service
    
    today = date.today()
    
    # Статистика за сегодня
    today_appointments_result = await session.execute(
        select(func.count(Appointment.id))
        .where(Appointment.appointment_date == today)
    )
    today_count = today_appointments_result.scalar()
    
    # Всего записей
    total_appointments_result = await session.execute(
        select(func.count(Appointment.id))
    )
    total_count = total_appointments_result.scalar()
    
    # Количество пациентов
    patients_result = await session.execute(select(func.count(Patient.id)))
    patients_count = patients_result.scalar()
    
    # Количество врачей
    doctors_result = await session.execute(
        select(func.count(Doctor.id)).where(Doctor.is_active == True)
    )
    doctors_count = doctors_result.scalar()
    
    # Записи по статусам
    status_counts = {}
    for status in AppointmentStatus:
        count_result = await session.execute(
            select(func.count(Appointment.id)).where(Appointment.status == status)
        )
        status_counts[status.value] = count_result.scalar()
    
    return {
        "today_appointments": today_count,
        "total_appointments": total_count,
        "total_patients": patients_count,
        "active_doctors": doctors_count,
        "appointments_by_status": status_counts,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development
    )