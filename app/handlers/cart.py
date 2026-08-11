"""Хэндлеры корзины и витрины услуг."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.data.knowledge import (
    CART_EMPTY_TEXT,
    ORDER_ALREADY_EXISTS_TEXT,
    ORDER_EMPTY_CART_TEXT,
    format_service_card,
    format_services_list,
)
from app.keyboards import (
    BTN_CART,
    BTN_SERVICES,
    add_to_cart_keyboard,
    cart_keyboard,
    main_menu,
    order_payment_keyboard,
    services_menu,
    showcase_services,
)
from app.services.cart import CartService
from app.services.orders import OrderService

router = Router(name="cart")


async def _user_db_id(message_or_cb: Message | CallbackQuery, cart: CartService) -> int:
    user = message_or_cb.from_user
    assert user is not None
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip() or None
    return await cart.ensure_user(user.id, user.username, full_name)


async def send_services_showcase(message: Message) -> None:
    await message.answer(format_services_list(), reply_markup=services_menu())
    for service in showcase_services():
        await message.answer(
            format_service_card(service),
            reply_markup=add_to_cart_keyboard(service),
        )


async def send_cart_view(
    message: Message,
    cart: CartService,
    user_id: int,
) -> None:
    items = await cart.get_items(user_id)
    text = cart.format_cart_text(items)
    await message.answer(
        text,
        reply_markup=cart_keyboard(items) if items else main_menu(),
    )


@router.message(Command("services"))
@router.message(F.text == BTN_SERVICES)
async def show_services_showcase(message: Message) -> None:
    await send_services_showcase(message)


@router.message(Command("cart"))
@router.message(F.text == BTN_CART)
async def show_cart(message: Message, cart_service: CartService) -> None:
    user_id = await _user_db_id(message, cart_service)
    await send_cart_view(message, cart_service, user_id)


@router.callback_query(F.data.startswith("cart:add:"))
async def cb_add_to_cart(
    callback: CallbackQuery,
    cart_service: CartService,
) -> None:
    data = callback.data or ""
    service_key = data.removeprefix("cart:add:")
    user_id = await _user_db_id(callback, cart_service)
    service = await cart_service.add_by_key(user_id, service_key)
    if service is None:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    await callback.answer(f"Добавлено: {service.title}")
    if callback.message:
        await callback.message.answer(
            f"Добавлено в корзину: {service.title}",
            reply_markup=main_menu(),
        )


@router.callback_query(F.data.startswith("cart:remove:"))
async def cb_remove_from_cart(
    callback: CallbackQuery,
    cart_service: CartService,
) -> None:
    data = callback.data or ""
    raw_id = data.removeprefix("cart:remove:")
    try:
        item_id = int(raw_id)
    except ValueError:
        await callback.answer("Некорректная позиция", show_alert=True)
        return

    user_id = await _user_db_id(callback, cart_service)
    removed = await cart_service.remove_item(user_id, item_id)
    if not removed:
        await callback.answer("Позиция уже удалена", show_alert=True)
    else:
        await callback.answer("Убрано из корзины")

    if callback.message:
        items = await cart_service.get_items(user_id)
        text = cart_service.format_cart_text(items)
        await callback.message.edit_text(
            text,
            reply_markup=cart_keyboard(items) if items else None,
        )


@router.callback_query(F.data == "cart:checkout")
async def cb_checkout(
    callback: CallbackQuery,
    cart_service: CartService,
    order_service: OrderService,
) -> None:
    user_id = await _user_db_id(callback, cart_service)
    result = await order_service.checkout(user_id)

    if result.empty_cart:
        await callback.answer(ORDER_EMPTY_CART_TEXT, show_alert=True)
        if callback.message:
            await callback.message.answer(CART_EMPTY_TEXT, reply_markup=main_menu())
        return

    assert result.order is not None
    if result.already_exists:
        await callback.answer(ORDER_ALREADY_EXISTS_TEXT, show_alert=True)
        text = order_service.format_order_text(result.order)
        if callback.message:
            await callback.message.answer(
                text,
                reply_markup=order_payment_keyboard(result.order),
            )
        return

    await callback.answer("Заказ оформлен")
    text = order_service.format_order_text(result.order)
    if callback.message:
        await callback.message.edit_text("Корзина оформлена.")
        await callback.message.answer(
            text + "\n\nНажмите «Оплатить», чтобы получить ссылку.",
            reply_markup=order_payment_keyboard(result.order),
        )
