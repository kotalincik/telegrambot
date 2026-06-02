"""
Дашборд администратора для управления клиникой.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import AppointmentStatus, Specialization, Doctor, Service, Appointment, Patient
from app.repositories import DoctorRepository, PatientRepository, AppointmentRepository, ServiceRepository
from app.services import BookingService
from app.config import settings


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Настройка шаблонов
templates = Jinja2Templates(directory="api/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(request: Request, session: AsyncSession = Depends(get_db)):
    """Главная страница дашборда."""
    today = date.today()
    
    # Статистика
    from sqlalchemy import func, select
    
    # Записи на сегодня
    today_appointments_result = await session.execute(
        select(Appointment).where(Appointment.appointment_date == today)
        .order_by(Appointment.start_time)
    )
    today_appointments = today_appointments_result.scalars().all()
    
    # Общая статистика
    stats = {
        "total_patients": (await session.execute(select(func.count(Patient.id)))).scalar(),
        "total_doctors": (await session.execute(
            select(func.count(Doctor.id)).where(Doctor.is_active == True)
        )).scalar(),
        "today_count": len(today_appointments),
        "pending_count": (await session.execute(
            select(func.count(Appointment.id)).where(Appointment.status == AppointmentStatus.SCHEDULED)
        )).scalar(),
    }
    
    # Статистика по статусам
    status_stats = {}
    for status in AppointmentStatus:
        count = (await session.execute(
            select(func.count(Appointment.id)).where(Appointment.status == status)
        )).scalar()
        status_stats[status.value] = count
    
    # Записи по дням недели (последние 7 дней)
    daily_stats = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = (await session.execute(
            select(func.count(Appointment.id)).where(Appointment.appointment_date == d)
        )).scalar()
        daily_stats.append({"date": d.strftime("%d.%m"), "count": count})
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "status_stats": status_stats,
        "daily_stats": daily_stats,
        "today_appointments": today_appointments,
        "today": today,
    })


@router.get("/doctors", response_class=HTMLResponse)
async def doctors_list(request: Request, session: AsyncSession = Depends(get_db)):
    """Список врачей."""
    repo = DoctorRepository(session)
    doctors = await repo.get_all()
    
    return templates.TemplateResponse("doctors.html", {
        "request": request,
        "doctors": doctors,
        "specializations": Specialization,
    })


@router.get("/doctors/{doctor_id}", response_class=HTMLResponse)
async def doctor_detail(request: Request, doctor_id: int, session: AsyncSession = Depends(get_db)):
    """Детальная страница врача."""
    repo = DoctorRepository(session)
    doctor = await repo.get_by_id(doctor_id)
    
    if not doctor:
        return RedirectResponse("/dashboard/doctors")
    
    # Записи врача
    from sqlalchemy import select
    appointments_result = await session.execute(
        select(Appointment).where(Appointment.doctor_id == doctor_id)
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
        .limit(20)
    )
    appointments = appointments_result.scalars().all()
    
    return templates.TemplateResponse("doctor_detail.html", {
        "request": request,
        "doctor": doctor,
        "appointments": appointments,
    })


@router.post("/doctors/{doctor_id}/toggle")
async def doctor_toggle_active(doctor_id: int, session: AsyncSession = Depends(get_db)):
    """Включить/выключить врача."""
    repo = DoctorRepository(session)
    doctor = await repo.get_by_id(doctor_id)
    
    if doctor:
        doctor.is_active = not doctor.is_active
        await session.commit()
    
    return RedirectResponse(url="/dashboard/doctors", status_code=303)


@router.get("/patients", response_class=HTMLResponse)
async def patients_list(
    request: Request, 
    search: str = "",
    session: AsyncSession = Depends(get_db)
):
    """Список пациентов."""
    from sqlalchemy import select
    
    query = select(Patient).order_by(Patient.created_at.desc())
    if search:
        query = query.where(Patient.full_name.ilike(f"%{search}%"))
    
    result = await session.execute(query.limit(50))
    patients = result.scalars().all()
    
    return templates.TemplateResponse("patients.html", {
        "request": request,
        "patients": patients,
        "search": search,
    })


@router.get("/patients/{patient_id}", response_class=HTMLResponse)
async def patient_detail(request: Request, patient_id: int, session: AsyncSession = Depends(get_db)):
    """Детальная страница пациента."""
    repo = PatientRepository(session)
    patient = await repo.get_by_id(patient_id)
    
    if not patient:
        return RedirectResponse("/dashboard/patients")
    
    # Записи пациента
    appointments = await repo.get_appointments(patient_id)
    
    return templates.TemplateResponse("patient_detail.html", {
        "request": request,
        "patient": patient,
        "appointments": appointments,
    })


@router.get("/appointments", response_class=HTMLResponse)
async def appointments_list(
    request: Request,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    session: AsyncSession = Depends(get_db)
):
    """Список записей с фильтрацией."""
    from sqlalchemy import select, and_
    
    query = select(Appointment).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
    
    conditions = []
    if status:
        try:
            status_enum = AppointmentStatus(status)
            conditions.append(Appointment.status == status_enum)
        except ValueError:
            pass
    
    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            conditions.append(Appointment.appointment_date >= d)
        except ValueError:
            pass
    
    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            conditions.append(Appointment.appointment_date <= d)
        except ValueError:
            pass
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await session.execute(query.limit(100))
    appointments = result.scalars().all()
    
    return templates.TemplateResponse("appointments.html", {
        "request": request,
        "appointments": appointments,
        "statuses": AppointmentStatus,
        "selected_status": status,
        "date_from": date_from,
        "date_to": date_to,
    })


@router.post("/appointments/{appointment_id}/cancel")
async def appointment_cancel_dashboard(
    appointment_id: int,
    reason: str = Form(""),
    session: AsyncSession = Depends(get_db)
):
    """Отмена записи из дашборда."""
    booking_service = BookingService(session)
    await booking_service.cancel_appointment(appointment_id, reason)
    
    return RedirectResponse(url="/dashboard/appointments", status_code=303)


@router.post("/appointments/{appointment_id}/confirm")
async def appointment_confirm_dashboard(
    appointment_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Подтверждение записи из дашборда."""
    repo = AppointmentRepository(session)
    await repo.confirm(appointment_id)
    
    return RedirectResponse(url="/dashboard/appointments", status_code=303)


@router.get("/services", response_class=HTMLResponse)
async def services_list(request: Request, session: AsyncSession = Depends(get_db)):
    """Список услуг."""
    from sqlalchemy import select
    result = await session.execute(select(Service).order_by(Service.name))
    services = result.scalars().all()
    
    return templates.TemplateResponse("services.html", {
        "request": request,
        "services": services,
        "specializations": Specialization,
    })


@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, session: AsyncSession = Depends(get_db)):
    """Страница статистики."""
    from sqlalchemy import func, select, extract
    from datetime import datetime
    
    today = date.today()
    
    # Общая статистика
    stats = {
        "total_patients": (await session.execute(select(func.count(Patient.id)))).scalar(),
        "total_doctors": (await session.execute(
            select(func.count(Doctor.id)).where(Doctor.is_active == True)
        )).scalar(),
        "total_appointments": (await session.execute(select(func.count(Appointment.id)))).scalar(),
        "total_services": (await session.execute(select(func.count(Service.id)))).scalar(),
    }
    
    # Записи по месяцам (последние 6 месяцев)
    monthly_stats = []
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30*i)
        start_of_month = month_date.replace(day=1)
        if i == 0:
            end_of_month = today
        else:
            next_month = (start_of_month + timedelta(days=32)).replace(day=1)
            end_of_month = next_month - timedelta(days=1)
        
        count = (await session.execute(
            select(func.count(Appointment.id))
            .where(Appointment.appointment_date >= start_of_month)
            .where(Appointment.appointment_date <= end_of_month)
        )).scalar()
        
        monthly_stats.append({
            "month": start_of_month.strftime("%b %Y"),
            "count": count
        })
    
    # Топ врачи по количеству записей
    top_doctors_result = await session.execute(
        select(Doctor, func.count(Appointment.id).label("appointment_count"))
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(Doctor.id)
        .order_by(func.count(Appointment.id).desc())
        .limit(5)
    )
    top_doctors = top_doctors_result.all()
    
    # Топ услуги
    top_services_result = await session.execute(
        select(Service, func.count(Appointment.id).label("service_count"))
        .join(Appointment, Appointment.service_id == Service.id)
        .group_by(Service.id)
        .order_by(func.count(Appointment.id).desc())
        .limit(5)
    )
    top_services = top_services_result.all()
    
    return templates.TemplateResponse("statistics.html", {
        "request": request,
        "stats": stats,
        "monthly_stats": monthly_stats,
        "top_doctors": top_doctors,
        "top_services": top_services,
    })