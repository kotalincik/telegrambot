# 🦷 Система записи к стоматологу (Dental Booking Bot)

Telegram-бот для записи пациентов на приём в стоматологическую клинику с админ-панелью и API.

## 📋 Описание проекта

Проект представляет собой полноценную систему автоматизации записи пациентов в стоматологическую клинику через Telegram-бота. Система включает:

- **Telegram Bot** — интерфейс для записи пациентов
- **FastAPI сервер** — REST API для администрирования
- **PostgreSQL база данных** — хранение данных
- **Alembic миграции** — управление схемой БД
- **Тестовое окружение** — pytest с async поддержкой

## 🏗 Архитектура

```
project/
├── app/                    # Основное приложение
│   ├── models.py          # SQLAlchemy ORM модели
│   ├── config.py          # Конфигурация
│   ├── database.py        # Подключение к БД
│   ├── repositories.py    # CRUD операции
│   └── services.py        # Бизнес-логика
├── bot/                    # Telegram bot
│   ├── main.py            # Точка входа
│   ├── handlers.py        # Обработчики команд
│   ├── keyboards.py       # Клавиатуры
│   ├── states.py          # FSM состояния
│   └── middleware.py      # Middleware
├── api/                    # FastAPI
│   └── main.py            # REST API endpoints
├── alembic/               # Миграции
├── tests/                 # Тесты
├── requirements.txt       # Зависимости
└── .env.example          # Пример конфигурации
```

## 🚀 Установка и запуск

### 1. Клонирование и настройка окружения

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфигурации
cp .env.example .env
# Отредактируйте .env — укажите BOT_TOKEN и настройки БД
```

### 2. Настройка базы данных PostgreSQL

```sql
CREATE DATABASE dental_bot;
CREATE USER postgres WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE dental_bot TO postgres;
```

### 3. Применение миграций (или создание таблиц)

```bash
# Автоматическое создание таблиц (development)
python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"

# Или через Alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Запуск бота

```bash
python bot/main.py
```

### 5. Запуск API сервера

```bash
python api/main.py
# или
uvicorn api.main:app --reload
```

## 🔧 Конфигурация (.env)

```bash
# Обязательные переменные
BOT_TOKEN=your_telegram_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_id

# База данных
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/dental_bot

# API сервер
API_HOST=0.0.0.0
API_PORT=8000
```

## 📱 Функционал бота

### Для пациентов:
- 🦷 **Запись на приём** — пошаговый выбор специализации, врача, услуги, даты и времени
- 📅 **Мои записи** — просмотр и отмена предстоящих записей
- 👤 **Профиль** — информация о пациенте
- 📞 **Контакты** — адрес и телефон клиники

### Для администраторов:
- 📊 Статистика клиники
- 📅 Записи на сегодня
- 👨‍⚕️ Управление врачами
- 📋 История записей

## 🔌 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Информация о сервисе |
| `/health` | GET | Проверка здоровья |
| `/api/doctors` | GET | Список врачей |
| `/api/doctors/{id}/schedule` | GET | Расписание врача |
| `/api/appointments` | GET | Список записей |
| `/api/appointments/{id}/cancel` | POST | Отмена записи |
| `/api/appointments/{id}/confirm` | POST | Подтверждение записи |
| `/api/statistics` | GET | Статистика клиники |

## 📊 Веб-дашборд (Web Dashboard)

Дашборд доступен по адресу `http://localhost:8000/dashboard/`

**Возможности дашборда:**

| Раздел | Описание |
|--------|----------|
| **Обзор** | Статистика, графики записей за 7 дней, записи на сегодня |
| **Записи** | Список всех записей с фильтрацией по статусу и дате |
| **Врачи** | Карточки врачей, активация/деактивация |
| **Пациенты** | Список пациентов с поиском |
| **Услуги** | Карточки услуг с ценами |
| **Статистика** | Аналитика, топ врачи и услуги, графики по месяцам |

**Технологии дашборда:**
- FastAPI + Jinja2 Templates
- Bootstrap 5 + Bootstrap Icons
- Chart.js для графиков

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием кода
pytest --cov=app --cov=bot --cov-report=html

# Конкретный файл тестов
pytest tests/test_services.py -v
```

## 📚 Стек технологий

| Компонент | Технология |
|-----------|------------|
| **Bot Framework** | aiogram 3.x |
| **Web Framework** | FastAPI |
| **ORM** | SQLAlchemy 2.0 |
| **Database** | PostgreSQL + asyncpg |
| **Migrations** | Alembic |
| **Testing** | pytest + pytest-asyncio |
| **Config** | pydantic-settings |
