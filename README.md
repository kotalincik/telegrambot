# Система записи к стоматологу 

Telegram-бот для записи пациентов на приём в стоматологическую клинику с админ-панелью и API.

## Установка и запуск

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

## Конфигурация (.env)

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

## Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием кода
pytest --cov=app --cov=bot --cov-report=html

# Конкретный файл тестов
pytest tests/test_services.py -v
```
