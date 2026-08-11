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
    # Сразу закрываем callback — создание платежа может занять несколько секунд
    await callback.answer("Готовлю ссылку на оплату…")

    raw = (callback.data or "").removeprefix("order:pay:")
    try:
        order_id = int(raw)
    except ValueError:
        if callback.message:
            await callback.message.answer("Некорректный заказ.", reply_markup=main_menu())
        return

    user_id = await _user_db_id(callback, cart_service)
    order = await order_service.get_order(order_id)
    if order is None or order.user_id != user_id:
        if callback.message:
            await callback.message.answer("Заказ не найден.", reply_markup=main_menu())
        return
    if order.status == "paid":
        if callback.message:
            await callback.message.answer(
                "Заказ уже оплачен.",
                reply_markup=main_menu(),
            )
        return
    if order.status != "awaiting_payment":
        if callback.message:
            await callback.message.answer(
                "Этот заказ нельзя оплатить.",
                reply_markup=main_menu(),
            )
        return

    try:
        order = await order_service.ensure_payment_link(order)
    except httpx.ConnectError:
        logger.exception("Нет связи с ЮKassa order_id=%s", order_id)
        if callback.message:
            await callback.message.answer(
                "Не удалось связаться с платёжным сервисом ЮKassa.\n"
                "Проверьте интернет на компьютере, где запущен бот, "
                "и доступ к api.yookassa.ru, затем нажмите «Оплатить» ещё раз.",
                reply_markup=order_payment_keyboard(order),
                parse_mode=None,
            )
        return
    except httpx.HTTPStatusError as exc:
        body = (exc.response.text or "")[:300]
        logger.exception(
            "ЮKassa HTTP %s order_id=%s body=%s",
            exc.response.status_code,
            order_id,
            body,
        )
        if callback.message:
            await callback.message.answer(
                "ЮKassa отклонила создание платежа. "
                "Проверьте shopId/секретный ключ в .env и попробуйте снова.",
                reply_markup=order_payment_keyboard(order),
                parse_mode=None,
            )
        return
    except httpx.HTTPError:
        logger.exception("Ошибка создания платежа ЮKassa order_id=%s", order_id)
        if callback.message:
            await callback.message.answer(
                "Не удалось создать ссылку на оплату. Попробуйте позже.",
                reply_markup=order_payment_keyboard(order),
                parse_mode=None,
            )
        return
    except Exception:
        logger.exception("Неожиданная ошибка оплаты order_id=%s", order_id)
        if callback.message:
            await callback.message.answer(
                "Не удалось создать ссылку на оплату. Попробуйте позже.",
                reply_markup=order_payment_keyboard(order),
                parse_mode=None,
            )
        return

    if not callback.message:
        return

    if not order.confirmation_url:
        await callback.message.answer(
            "Платёж создан, но ссылка на оплату пустая. "
            "Проверьте настройки магазина ЮKassa.",
            reply_markup=order_payment_keyboard(order),
            parse_mode=None,
        )
        return

    await callback.message.answer(
        "Ссылка на оплату заказа:\n"
        f"{order.confirmation_url}\n\n"
        "Откройте ссылку, оплатите и вернитесь в чат — нажмите «Я оплатил».",
        reply_markup=order_payment_keyboard(order, payment_url=order.confirmation_url),
        parse_mode=None,
    )


@router.callback_query(F.data.startswith("order:paid:"))
async def cb_i_paid(
    callback: CallbackQuery,
    cart_service: CartService,
    order_service: OrderService,
) -> None:
    await callback.answer("Проверяю оплату…")

    raw = (callback.data or "").removeprefix("order:paid:")
    try:
        order_id = int(raw)
    except ValueError:
        if callback.message:
            await callback.message.answer("Некорректный заказ.", reply_markup=main_menu())
        return

    user_id = await _user_db_id(callback, cart_service)
    try:
        result = await order_service.check_payment(order_id, user_id)
    except httpx.ConnectError:
        logger.exception("Нет связи с ЮKassa при проверке order_id=%s", order_id)
        if callback.message:
            await callback.message.answer(
                "Не удалось связаться с ЮKassa для проверки платежа. "
                "Проверьте интернет на компьютере с ботом и попробуйте снова.",
                reply_markup=main_menu(),
                parse_mode=None,
            )
        return
    except httpx.HTTPError:
        logger.exception("Ошибка проверки платежа ЮKassa order_id=%s", order_id)
        if callback.message:
            await callback.message.answer(
                "Не удалось проверить оплату. Попробуйте позже.",
                reply_markup=main_menu(),
                parse_mode=None,
            )
        return

    if callback.message:
        await callback.message.answer(
            result.message,
            reply_markup=main_menu(),
            parse_mode=None,
        )
