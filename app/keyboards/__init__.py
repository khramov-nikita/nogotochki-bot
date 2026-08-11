"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.data.knowledge import SERVICES, Service
from app.db.repository import CartItem, Order

BTN_SERVICES = "Услуги и цены"
BTN_CART = "Корзина"
BTN_FAQ = "Частые вопросы"
BTN_BOOKING = "Запись"
BTN_ABOUT = "О студии"
BTN_CONTACT = "Связаться с человеком"
BTN_BACK = "« В меню"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_CART)],
            [KeyboardButton(text=BTN_FAQ), KeyboardButton(text=BTN_BOOKING)],
            [KeyboardButton(text=BTN_ABOUT), KeyboardButton(text=BTN_CONTACT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню…",
    )


def services_menu() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=BTN_CART)],
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Листайте карточки услуг…",
    )


def add_to_cart_keyboard(service: Service) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить в корзину",
                    callback_data=f"cart:add:{service.key}",
                )
            ]
        ]
    )


def cart_keyboard(items: list[CartItem]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Убрать: {item.title[:28]}",
                    callback_data=f"cart:remove:{item.id}",
                )
            ]
        )
    if items:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Оформить заказ",
                    callback_data="cart:checkout",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_payment_keyboard(
    order: Order,
    payment_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url:
        rows.append(
            [InlineKeyboardButton(text="Открыть страницу оплаты", url=payment_url)]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Оплатить" if not payment_url else "Обновить ссылку",
                callback_data=f"order:pay:{order.id}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Я оплатил",
                callback_data=f"order:paid:{order.id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def showcase_services() -> list[Service]:
    return list(SERVICES)
