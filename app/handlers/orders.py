"""Хэндлеры заказов и оплаты ЮKassa."""

from __future__ import annotations

import logging

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu, order_payment_keyboard
from app.services.cart import CartService
from app.services.orders import OrderService

logger = logging.getLogger(__name__)

router = Router(name="orders")


async def _user_db_id(message_or_cb: Message | CallbackQuery, cart: CartService) -> int:
    user = message_or_cb.from_user
    assert user is not None
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip() or None
    return await cart.ensure_user(user.id, user.username, full_name)


@router.message(Command("order"))
async def show_active_order(
    message: Message,
    cart_service: CartService,
    order_service: OrderService,
) -> None:
    user_id = await _user_db_id(message, cart_service)
    order = await order_service.get_active_order(user_id)
    if order is None:
        await message.answer(
            "Нет заказа, ожидающего оплаты. Оформите заказ из корзины.",
            reply_markup=main_menu(),
        )
        return
    await message.answer(
        order_service.format_order_text(order),
        reply_markup=order_payment_keyboard(order),
    )


@router.callback_query(F.data.startswith("order:pay:"))
async def cb_pay(
    callback: CallbackQuery,
    cart_service: CartService,
    order_service: OrderService,
) -> None:
    raw = (callback.data or "").removeprefix("order:pay:")
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer("Некорректный заказ", show_alert=True)
        return

    user_id = await _user_db_id(callback, cart_service)
    order = await order_service.get_order(order_id)
    if order is None or order.user_id != user_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order.status == "paid":
        await callback.answer("Заказ уже оплачен", show_alert=True)
        return
    if order.status != "awaiting_payment":
        await callback.answer("Заказ нельзя оплатить", show_alert=True)
        return

    try:
        order = await order_service.ensure_payment_link(order)
    except httpx.HTTPError:
        logger.exception("Ошибка создания платежа ЮKassa order_id=%s", order_id)
        await callback.answer(
            "Не удалось создать ссылку на оплату. Попробуйте позже.",
            show_alert=True,
        )
        return

    await callback.answer()
    if callback.message and order.confirmation_url:
        await callback.message.answer(
            "Ссылка на оплату:\n"
            f"{order.confirmation_url}\n\n"
            "После оплаты вернитесь в чат и нажмите «Я оплатил».",
            reply_markup=order_payment_keyboard(order),
            parse_mode=None,
        )


@router.callback_query(F.data.startswith("order:paid:"))
async def cb_i_paid(
    callback: CallbackQuery,
    cart_service: CartService,
    order_service: OrderService,
) -> None:
    raw = (callback.data or "").removeprefix("order:paid:")
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer("Некорректный заказ", show_alert=True)
        return

    user_id = await _user_db_id(callback, cart_service)
    try:
        result = await order_service.check_payment(order_id, user_id)
    except httpx.HTTPError:
        logger.exception("Ошибка проверки платежа ЮKassa order_id=%s", order_id)
        await callback.answer(
            "Не удалось проверить оплату. Попробуйте позже.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Оплата подтверждена" if result.paid else "Платёж не подтверждён",
        show_alert=not result.paid,
    )
    if callback.message:
        await callback.message.answer(
            result.message,
            reply_markup=main_menu(),
            parse_mode=None,
        )
