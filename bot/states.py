"""
Состояния FSM (Finite State Machine) для бота.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния для процесса записи на приём."""
    selecting_specialization = State()  # Выбор специализации
    selecting_doctor = State()          # Выбор врача
    selecting_service = State()         # Выбор услуги
    selecting_date = State()            # Выбор даты
    selecting_time = State()            # Выбор времени
    confirming = State()                # Подтверждение записи
    adding_notes = State()              # Добавление примечаний (опционально)


class ProfileStates(StatesGroup):
    """Состояния для управления профилем."""
    editing_name = State()
    editing_phone = State()


class AdminStates(StatesGroup):
    """Состояния для админ-функций."""
    viewing_appointments = State()
    managing_doctors = State()