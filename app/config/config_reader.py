"""Config reader using pydantic-settings.

Этот модуль показывает, как читать переменные окружения и `.env` файл
в кодировке UTF-8 с помощью `pydantic-settings` (совместимо с pydantic v2).

Usage:
    from app.config.config_reader import get_settings

    settings = get_settings()
    host = settings.redis_host

Файлы `.env` будут прочитаны автоматически в кодировке UTF-8 благодаря
параметру `env_file_encoding` в `SettingsConfigDict`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings read from environment / .env (UTF-8).

    Добавляйте сюда поля, которые нужны приложению. По умолчанию значения
    будут браться из переменных окружения, а при отсутствии — использовать
    значения по умолчанию, указанные ниже.
    """

    # Redis (env names are defined explicitly to match .env/.env.template)
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")
    # redis_stream: str = Field("new_car_notify_stream", env="REDIS_STREAM")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")

    # Дополнительные настройки
    env: str = Field("development", env="ENV")

    # pydantic-settings configuration: указываем .env и кодировку UTF-8
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        # можно добавить другие опции при необходимости
    )


@lru_cache()
def get_settings() -> Settings:
    """Возвращает кешированный экземпляр `Settings`.

    lru_cache обеспечивает, что настройки будут прочитаны один раз при
    первом вызове и потом переиспользоваться (удобно для FastAPI зависимостей).
    """

    return Settings()

env_config = get_settings()

__all__ = ["Settings", "get_settings", "env_config"]