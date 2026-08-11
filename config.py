"""Конфигурация бота из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """Ошибка конфигурации."""


@dataclass(frozen=True)
class Config:
    bot_token: str


def load_config() -> Config:
    load_dotenv()
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        raise ConfigError(
            "Не задан BOT_TOKEN. Скопируйте .env.example в .env и укажите токен бота."
        )
    return Config(bot_token=token)
