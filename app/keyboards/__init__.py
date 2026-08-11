"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.data.knowledge import SERVICES

BTN_SERVICES = "Услуги и цены"
BTN_FAQ = "Частые вопросы"
BTN_BOOKING = "Запись"
BTN_ABOUT = "О студии"
BTN_BACK = "« В меню"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_FAQ)],
            [KeyboardButton(text=BTN_BOOKING), KeyboardButton(text=BTN_ABOUT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню…",
    )


def services_menu() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    titles = [s.title for s in SERVICES]
    for i in range(0, len(titles), 1):
        rows.append([KeyboardButton(text=titles[i])])
    rows.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите услугу…",
    )
