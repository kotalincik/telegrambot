"""
Конфигурация приложения.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./dental_bot.db"
    
    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_USER_ID: int
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # Mode
    MODE: str = "development"
    
    @property
    def is_development(self) -> bool:
        return self.MODE.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return self.MODE.lower() == "production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()