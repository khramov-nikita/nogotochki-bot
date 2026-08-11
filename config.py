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
    deepseek_api_key: str
    deepseek_model: str
    deepseek_base_url: str
    admin_name: str
    admin_telegram: str
    admin_phone: str


def load_config() -> Config:
    load_dotenv()
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        raise ConfigError(
            "Не задан BOT_TOKEN. Скопируйте .env.example в .env и укажите токен бота."
        )

    deepseek_api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not deepseek_api_key:
        raise ConfigError(
            "Не задан DEEPSEEK_API_KEY. Добавьте ключ DeepSeek в .env."
        )

    deepseek_model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
    deepseek_base_url = (
        os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    ).strip()

    admin_name = (os.getenv("ADMIN_NAME") or "Администратор студии").strip()
    admin_telegram = (os.getenv("ADMIN_TELEGRAM") or "").strip().lstrip("@")
    admin_phone = (os.getenv("ADMIN_PHONE") or "").strip()

    return Config(
        bot_token=token,
        deepseek_api_key=deepseek_api_key,
        deepseek_model=deepseek_model,
        deepseek_base_url=deepseek_base_url,
        admin_name=admin_name,
        admin_telegram=admin_telegram,
        admin_phone=admin_phone,
    )
