from functools import lru_cache
import json
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cryptoquant"
    SECRET_KEY: str = "change-me-in-production-secret-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379/0"
    AES_SECRET_KEY: str = "change-me-aes-key-must-be-32byt"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    APP_NAME: str = "CryptoQuant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.startswith("["):
            return json.loads(self.CORS_ORIGINS)
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
