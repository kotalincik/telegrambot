"""
Основные обработчики команд и callback для бота.
"""

from datetime import date, datetime, time
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Specialization, AppointmentStatus
from app.services import BookingService, ScheduleService
from bot.states import BookingStates
from bot import keyboards as kb
from bot.middleware import DbSessionMiddleware


router = Router()
router.message.middleware(DbSessionMiddleware())
router.callback_query.middleware(DbSessionMiddleware())


# ======== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========

def is_admin(telegram_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return telegram_id == settings.ADMIN_USER_ID


def format_appointment_info(appointment) -> str:
    """Форматировать информацию о записи."""
    status_text = {
        "scheduled": "⏳ Запланировано",
        "confirmed": "✅ Подтверждено",
        "completed": "🏁 Завершено",
        "cancelled": "❌ Отменено",
    }.get(appointment.status.value, appointment.status.value)
    
    return f"""
<b>🦷 Запись на приём #{appointment.id}</b>

👨‍⚕️ <b>Врач:</b> {appointment.doctor.full_name}
🩺 <b>Услуга:</b> {appointment.service.name}
📅 <b>Дата:</b> {appointment.appointment_date.strftime("%d.%m.%Y")}
⏰ <b>Время:</b> {appointment.start_time.strftime("%H:%M")} - {appointment.end_time.strftime("%H:%M")}
💰 <b>Стоимость:</b> {appointment.service.base_price}₽
📊 <b>Статус:</b> {status_text}
"""


# ======== КОМАНДЫ ========

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Обработчик /start."""
    # Регистрируем или получаем пациента
    booking_service = BookingService(session)
    patient = await booking_service.get_or_create_patient(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
    )
    
    welcome_text = f"""
👋 <b>Добро пожаловать, {patient.full_name}!</b>

🦷 Я бот для записи в стоматологическую клинику.
С моей помощью вы можете:
• Записаться на приём к нужному специалисту
• Просмотреть свои записи
• Отменить запись при необходимости

Выберите действие в меню ниже:
"""
    await message.answer(
        welcome_text,
        reply_markup=kb.get_main_menu_keyboard(is_admin(message.from_user.id)),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик /help."""
    help_text = """
<b>📖 Помощь по боту</b>

<b>Команды:</b>
/start — Начать работу с ботом
/help — Показать эту справку
/menu — Главное меню

<b>Как записаться:</b>
1. Нажмите «🦷 Записаться на приём»
2. Выберите специализацию врача
3. Выберите конкретного врача
4. Выберите нужную услугу
5. Выберите удобную дату и время
6. Подтвердите запись

<b>Управление записями:</b>
Используйте раздел «📅 Мои записи» для просмотра и отмены записей.
"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "🏠 В меню")
@router.message(Command("menu"))
async def show_menu(message: Message):
    """Показать главное меню."""
    await message.answer(
        "Главное меню:",
        reply_markup=kb.get_main_menu_keyboard(is_admin(message.from_user.id))
    )


# ======== ЗАПИСЬ НА ПРИЁМ ========

@router.message(F.text == "🦷 Записаться на приём")
async def start_booking(message: Message, state: FSMContext):
    """Начало процесса записи."""
    await state.set_state(BookingStates.selecting_specialization)
    await message.answer(
        "<b>🦷 Запись на приём</b>\n\nВыберите специализацию врача:",
        reply_markup=kb.get_specialization_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("spec:"), BookingStates.selecting_specialization)
async def select_specialization(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор специализации."""
    spec_value = callback.data.split(":")[1]
    specialization = Specialization(spec_value)
    
    # Сохраняем выбор
    await state.update_data(specialization=specialization.value)
    
    # Получаем врачей
    booking_service = BookingService(session)
    doctors = await booking_service.get_doctors_by_specialization(specialization)
    
    if not doctors:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет доступных врачей с такой специализацией.\n"
            "Попробуйте выбрать другую специализацию или свяжитесь с клиникой.",
            reply_markup=kb.get_specialization_keyboard()
        )
        return
    
    await state.set_state(BookingStates.selecting_doctor)
    await callback.message.edit_text(
        f"<b>Выбрана специализация:</b> {specialization.value}\n\n"
        f"Выберите врача:",
        reply_markup=kb.get_doctors_keyboard(doctors),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("doctor:"), BookingStates.selecting_doctor)
async def select_doctor(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор врача."""
    doctor_id = int(callback.data.split(":")[1])
    await state.update_data(doctor_id=doctor_id)
    
    # Получаем услуги врача (по специализации)
    data = await state.get_data()
    specialization = Specialization(data["specialization"])
    
    booking_service = BookingService(session)
    services = await booking_service.get_services_by_specialization(specialization)
    
    await state.set_state(BookingStates.selecting_service)
    await callback.message.edit_text(
        "Выберите услугу:",
        reply_markup=kb.get_services_keyboard(services)
    )


@router.callback_query(F.data.startswith("service:"), BookingStates.selecting_service)
async def select_service(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор услуги."""
    service_id = int(callback.data.split(":")[1])
    await state.update_data(service_id=service_id)
    
    # Получаем доступные даты
    data = await state.get_data()
    doctor_id = data["doctor_id"]
    
    booking_service = BookingService(session)
    available_dates = await booking_service.get_available_dates(doctor_id, days_ahead=14)
    
    if not available_dates:
        await callback.message.edit_text(
            "😔 К сожалению, у выбранного врача нет свободных дат в ближайшие 2 недели.\n"
            "Попробуйте выбрать другого врача.",
            reply_markup=kb.get_specialization_keyboard()
        )
        await state.clear()
        return
    
    await state.set_state(BookingStates.selecting_date)
    await callback.message.edit_text(
        "Выберите удобную дату:",
        reply_markup=kb.get_dates_keyboard(available_dates)
    )


@router.callback_query(F.data.startswith("date:"), BookingStates.selecting_date)
async def select_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор даты."""
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    await state.update_data(appointment_date=date_str)
    
    # Получаем доступное время
    data = await state.get_data()
    doctor_id = data["doctor_id"]
    
    schedule_service = ScheduleService(session)
    time_slots = await schedule_service.get_available_slots(doctor_id, selected_date)
    
    if not time_slots:
        await callback.message.edit_text(
            "😔 К сожалению, на эту дату нет свободного времени.\n"
            "Пожалуйста, выберите другую дату.",
            reply_markup=kb.get_dates_keyboard([selected_date])  # Вернемся к выбору даты
        )
        return
    
    await state.set_state(BookingStates.selecting_time)
    await callback.message.edit_text(
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"Выберите время:",
        reply_markup=kb.get_times_keyboard(time_slots),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("time:"), BookingStates.selecting_time)
async def select_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор времени — показываем подтверждение."""
    time_str = callback.data.split(":")[1]
    await state.update_data(start_time=time_str)
    
    # Получаем полные данные для подтверждения
    data = await state.get_data()
    
    # Получаем информацию о враче и услуге
    from app.repositories import DoctorRepository, ServiceRepository
    doctor_repo = DoctorRepository(session)
    service_repo = ServiceRepository(session)
    
    doctor = await doctor_repo.get_by_id(data["doctor_id"])
    service = await service_repo.get_by_id(data["service_id"])
    appointment_date = datetime.strptime(data["appointment_date"], "%Y-%m-%d").date()
    start_time = datetime.strptime(data["start_time"], "%H:%M").time()
    end_time = (datetime.combine(date.today(), start_time) + 
                __import__('datetime').timedelta(minutes=service.duration_minutes)).time()
    
    # Сохраняем end_time
    await state.update_data(end_time=end_time.strftime("%H:%M"))
    
    confirm_text = f"""
<b>📋 Подтвердите запись:</b>

👨‍⚕️ <b>Врач:</b> {doctor.full_name}
🩺 <b>Услуга:</b> {service.name}
📅 <b>Дата:</b> {appointment_date.strftime('%d.%m.%Y')}
⏰ <b>Время:</b> {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}
💰 <b>Стоимость:</b> {service.base_price}₽

Всё верно?
"""
    await state.set_state(BookingStates.confirming)
    await callback.message.edit_text(
        confirm_text,
        reply_markup=kb.get_confirmation_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm:yes", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение записи."""
    data = await state.get_data()
    
    # Создаём запись
    booking_service = BookingService(session)
    patient = await booking_service.get_or_create_patient(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name
    )
    
    success, message = await booking_service.book_appointment(
        patient_id=patient.id,
        doctor_id=data["doctor_id"],
        service_id=data["service_id"],
        appointment_date=datetime.strptime(data["appointment_date"], "%Y-%m-%d").date(),
        start_time=datetime.strptime(data["start_time"], "%H:%M").time(),
        end_time=datetime.strptime(data["end_time"], "%H:%M").time(),
    )
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Запись успешно создана!</b>\n\n"
            f"Ждём вас в клинике. Не забудьте прийти за 10 минут до назначенного времени.\n\n"
            f"За день до приёма мы пришлём напоминание.",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании записи:</b>\n{message}\n\n"
            f"Пожалуйста, попробуйте снова.",
            parse_mode="HTML"
        )
    
    await state.clear()


# ======== МОИ ЗАПИСИ ========

@router.message(F.text == "📅 Мои записи")
async def show_appointments(message: Message, session: AsyncSession):
    """Показать записи пациента."""
    booking_service = BookingService(session)
    patient = await booking_service.get_or_create_patient(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name
    )
    
    appointments = await booking_service.get_patient_appointments(
        patient_id=patient.id,
        upcoming_only=True
    )
    
    if not appointments:
        await message.answer(
            "📭 У вас пока нет предстоящих записей.\n\n"
            "Хотите записаться на приём?",
            reply_markup=kb.get_main_menu_keyboard(is_admin(message.from_user.id))
        )
        return
    
    await message.answer(
        "<b>📅 Ваши предстоящие записи:</b>",
        reply_markup=kb.get_appointments_keyboard(appointments),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_appoint:"))
async def view_appointment(callback: CallbackQuery, session: AsyncSession):
    """Просмотр конкретной записи."""
    appointment_id = int(callback.data.split(":")[1])
    
    from app.repositories import AppointmentRepository
    repo = AppointmentRepository(session)
    appointment = await repo.get_by_id(appointment_id)
    
    if not appointment:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    
    # Проверяем, что это запись текущего пользователя или админа
    booking_service = BookingService(session)
    patient = await booking_service.get_or_create_patient(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name
    )
    
    if appointment.patient_id != patient.id and not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой записи", show_alert=True)
        return
    
    can_cancel = appointment.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
    
    await callback.message.edit_text(
        format_appointment_info(appointment),
        reply_markup=kb.get_appointment_actions_keyboard(appointment_id, can_cancel),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cancel_appoint:"))
async def cancel_appointment_start(callback: CallbackQuery):
    """Начало отмены записи."""
    appointment_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите отменить запись?</b>\n\n"
        "Это действие нельзя отменить.",
        reply_markup=kb.get_cancel_confirmation_keyboard(appointment_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm_cancel:"))
async def confirm_cancel(callback: CallbackQuery, session: AsyncSession):
    """Подтверждение отмены."""
    appointment_id = int(callback.data.split(":")[1])
    
    booking_service = BookingService(session)
    success, message = await booking_service.cancel_appointment(appointment_id)
    
    if success:
        await callback.message.edit_text(
            "✅ <b>Запись отменена.</b>\n\n"
            "Если хотите записаться на другое время, используйте меню.",
            parse_mode="HTML"
        )
    else:
        await callback.answer("Не удалось отменить запись", show_alert=True)


# ======== ОБРАТНАЯ НАВИГАЦИЯ ========

@router.callback_query(F.data == "back:spec")
async def back_to_specialization(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору специализации."""
    await state.set_state(BookingStates.selecting_specialization)
    await callback.message.edit_text(
        "<b>🦷 Запись на приём</b>\n\nВыберите специализацию врача:",
        reply_markup=kb.get_specialization_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back:doctor")
async def back_to_doctor(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Назад к выбору врача."""
    data = await state.get_data()
    specialization = Specialization(data["specialization"])
    
    booking_service = BookingService(session)
    doctors = await booking_service.get_doctors_by_specialization(specialization)
    
    await state.set_state(BookingStates.selecting_doctor)
    await callback.message.edit_text(
        f"<b>Выбрана специализация:</b> {specialization.value}\n\n"
        f"Выберите врача:",
        reply_markup=kb.get_doctors_keyboard(doctors),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back:service")
async def back_to_service(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Назад к выбору услуги."""
    data = await state.get_data()
    specialization = Specialization(data["specialization"])
    
    booking_service = BookingService(session)
    services = await booking_service.get_services_by_specialization(specialization)
    
    await state.set_state(BookingStates.selecting_service)
    await callback.message.edit_text(
        "Выберите услугу:",
        reply_markup=kb.get_services_keyboard(services)
    )


@router.callback_query(F.data == "back:date")
async def back_to_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Назад к выбору даты."""
    data = await state.get_data()
    doctor_id = data["doctor_id"]
    
    booking_service = BookingService(session)
    available_dates = await booking_service.get_available_dates(doctor_id, days_ahead=14)
    
    await state.set_state(BookingStates.selecting_date)
    await callback.message.edit_text(
        "Выберите удобную дату:",
        reply_markup=kb.get_dates_keyboard(available_dates)
    )


@router.callback_query(F.data == "back:time")
async def back_to_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Назад к выбору времени."""
    data = await state.get_data()
    doctor_id = data["doctor_id"]
    appointment_date = datetime.strptime(data["appointment_date"], "%Y-%m-%d").date()
    
    schedule_service = ScheduleService(session)
    time_slots = await schedule_service.get_available_slots(doctor_id, appointment_date)
    
    await state.set_state(BookingStates.selecting_time)
    await callback.message.edit_text(
        f"Дата: <b>{appointment_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"Выберите время:",
        reply_markup=kb.get_times_keyboard(time_slots),
        parse_mode="HTML"
    )


# ======== ОТМЕНА ЗАПИСИ ========

@router.callback_query(F.data == "cancel:booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса записи."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись отменена.\n\n"
        "Вы можете начать заново в любое время через меню."
    )


# ======== ДРУГИЕ РАЗДЕЛЫ ========

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, session: AsyncSession):
    """Показать профиль."""
    booking_service = BookingService(session)
    patient = await booking_service.get_or_create_patient(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name
    )
    
    profile_text = f"""
<b>👤 Ваш профиль</b>

🆔 <b>Telegram ID:</b> {patient.telegram_id}
👤 <b>Имя:</b> {patient.full_name}
📞 <b>Телефон:</b> {patient.phone or 'Не указан'}
🎂 <b>Дата рождения:</b> {patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else 'Не указана'}
📅 <b>Дата регистрации:</b> {patient.created_at.strftime('%d.%m.%Y')}

<i>Для изменения данных свяжитесь с администратором клиники.</i>
"""
    await message.answer(profile_text, parse_mode="HTML")


@router.message(F.text == "📞 Контакты клиники")
async def show_contacts(message: Message):
    """Показать контакты клиники."""
    contacts_text = """
<b>🏥 Стоматологическая клиника</b>

📍 <b>Адрес:</b> г. Москва, ул. Примерная, д. 123
📞 <b>Телефон:</b> +7 (999) 123-45-67
📧 <b>Email:</b> info@dental-clinic.ru
🌐 <b>Сайт:</b> www.dental-clinic.ru

<b>⏰ Режим работы:</b>
Пн-Пт: 9:00 - 20:00
Сб: 10:00 - 18:00
Вс: Выходной

<i>Экстренная помощь: круглосуточно</i>
"""
    await message.answer(contacts_text, parse_mode="HTML")


# ======== АДМИН-ПАНЕЛЬ ========

@router.message(F.text == "⚙️ Администратор")
async def admin_panel(message: Message):
    """Админ-панель."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой функции.")
        return
    
    await message.answer(
        "<b>⚙️ Панель администратора</b>",
        reply_markup=kb.get_admin_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:today")
async def admin_today_appointments(callback: CallbackQuery, session: AsyncSession):
    """Записи на сегодня (админ)."""
    from app.repositories import AppointmentRepository
    repo = AppointmentRepository(session)
    
    today = date.today()
    # Получаем все записи на сегодня
    from sqlalchemy import select
    from app.models import Appointment
    
    result = await session.execute(
        select(Appointment)
        .where(Appointment.appointment_date == today)
        .order_by(Appointment.start_time)
    )
    appointments = result.scalars().all()
    
    if not appointments:
        await callback.message.edit_text(
            "📭 На сегодня записей нет.",
            reply_markup=kb.get_admin_menu_keyboard()
        )
        return
    
    text = f"<b>📅 Записи на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n\n"
    for app in appointments:
        status_emoji = {
            "scheduled": "🟡",
            "confirmed": "🟢",
            "completed": "✅",
            "cancelled": "❌",
        }.get(app.status.value, "⚪")
        
        text += (f"{status_emoji} <b>{app.start_time.strftime('%H:%M')}</b> - "
                f"{app.patient.full_name} - "
                f"{app.doctor.full_name} - "
                f"{app.service.name}\n")
    
    await callback.message.edit_text(text, reply_markup=kb.get_admin_menu_keyboard(), parse_mode="HTML")


# ======== МЕНЮ ========

@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=None
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=kb.get_main_menu_keyboard(is_admin(callback.from_user.id))
    )