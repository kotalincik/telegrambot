"""
Клавиатуры для Telegram бота.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from app.models import Specialization


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню."""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="🦷 Записаться на приём")
    builder.button(text="📅 Мои записи")
    builder.button(text="👤 Профиль")
    builder.button(text="📞 Контакты клиники")
    
    if is_admin:
        builder.button(text="⚙️ Администратор")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_specialization_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора специализации."""
    builder = InlineKeyboardBuilder()
    
    specializations = [
        (Specialization.THERAPIST, "🦷 Терапевт"),
        (Specialization.SURGEON, "🔪 Хирург"),
        (Specialization.ORTHOPEDIST, "🦴 Ортопед"),
        (Specialization.ORTHODONTIST, "😁 Ортодонт"),
        (Specialization.PERIODONTIST, "🦷 Пародонтолог"),
        (Specialization.PEDODONTIST, "👶 Детский стоматолог"),
        (Specialization.ENDODONTIST, "🔍 Эндодонтист"),
        (Specialization.IMPLANTOLOGIST, "🦷 Имплантолог"),
    ]
    
    for spec, label in specializations:
        builder.button(text=label, callback_data=f"spec:{spec.value}")
    
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def get_doctors_keyboard(doctors: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора врача."""
    builder = InlineKeyboardBuilder()
    
    for doctor in doctors:
        builder.button(
            text=f"👨‍⚕️ {doctor.full_name}",
            callback_data=f"doctor:{doctor.id}"
        )
    
    builder.button(text="⬅️ Назад", callback_data="back:spec")
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(1)
    return builder.as_markup()


def get_services_keyboard(services: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора услуги."""
    builder = InlineKeyboardBuilder()
    
    for service in services:
        builder.button(
            text=f"{service.name} - {service.base_price}₽",
            callback_data=f"service:{service.id}"
        )
    
    builder.button(text="⬅️ Назад", callback_data="back:doctor")
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(1)
    return builder.as_markup()


def get_dates_keyboard(dates: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты."""
    builder = InlineKeyboardBuilder()
    
    for date_obj in dates:
        date_str = date_obj.strftime("%Y-%m-%d")
        display_str = date_obj.strftime("%d.%m.%Y (%a)")
        builder.button(
            text=display_str,
            callback_data=f"date:{date_str}"
        )
    
    builder.button(text="⬅️ Назад", callback_data="back:service")
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(2)
    return builder.as_markup()


def get_times_keyboard(time_slots: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени."""
    builder = InlineKeyboardBuilder()
    
    for start_time, end_time in time_slots:
        time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        builder.button(
            text=time_str,
            callback_data=f"time:{start_time.strftime('%H:%M')}"
        )
    
    builder.button(text="⬅️ Назад", callback_data="back:date")
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(3)
    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Подтвердить запись", callback_data="confirm:yes")
    builder.button(text="⬅️ Назад", callback_data="back:time")
    builder.button(text="❌ Отмена", callback_data="cancel:booking")
    builder.adjust(1)
    return builder.as_markup()


def get_appointments_keyboard(appointments: list) -> InlineKeyboardMarkup:
    """Клавиатура управления записями."""
    builder = InlineKeyboardBuilder()
    
    for app in appointments:
        date_str = app.appointment_date.strftime("%d.%m")
        time_str = app.start_time.strftime("%H:%M")
        status_emoji = {
            "scheduled": "🟡",
            "confirmed": "🟢",
            "completed": "✅",
            "cancelled": "❌",
        }.get(app.status.value, "⚪")
        
        builder.button(
            text=f"{status_emoji} {date_str} {time_str} - {app.service.name[:20]}",
            callback_data=f"view_appoint:{app.id}"
        )
    
    builder.button(text="🔄 Обновить", callback_data="refresh:appointments")
    builder.button(text="🏠 В меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def get_appointment_actions_keyboard(appointment_id: int, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура действий с конкретной записью."""
    builder = InlineKeyboardBuilder()
    
    if can_cancel:
        builder.button(
            text="❌ Отменить запись",
            callback_data=f"cancel_appoint:{appointment_id}"
        )
    
    builder.button(text="⬅️ Назад к списку", callback_data="back:appointments")
    builder.button(text="🏠 В меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_confirmation_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены."""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="⚠️ Да, отменить запись",
        callback_data=f"confirm_cancel:{appointment_id}"
    )
    builder.button(text="⬅️ Назад", callback_data=f"view_appoint:{appointment_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Админ-меню."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="📅 Все записи на сегодня", callback_data="admin:today")
    builder.button(text="👨‍⚕️ Управление врачами", callback_data="admin:doctors")
    builder.button(text="📋 История записей", callback_data="admin:history")
    builder.button(text="🏠 В меню", callback_data="menu:main")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены действия."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )