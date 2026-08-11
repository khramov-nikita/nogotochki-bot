"""Хэндлеры пользователя: меню и сценарии из паспорта."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.data.knowledge import (
    ABOUT_TEXT,
    BOOKING_TEXT,
    CONTACT_UNAVAILABLE_TEXT,
    HELP_TEXT,
    WELCOME_TEXT,
    format_admin_contact_text,
    format_faq,
)
from app.keyboards import (
    BTN_ABOUT,
    BTN_BACK,
    BTN_BOOKING,
    BTN_CONTACT,
    BTN_FAQ,
    main_menu,
)
from app.services.cart import CartService
from app.services.deepseek import DeepSeekService
from config import Config

router = Router(name="user")


async def _ensure_user(message: Message, cart: CartService) -> None:
    user = message.from_user
    if user is None:
        return
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip() or None
    await cart.ensure_user(user.id, user.username, full_name)


@router.message(CommandStart())
async def cmd_start(message: Message, cart_service: CartService) -> None:
    await _ensure_user(message, cart_service)
    payload = (message.text or "").split(maxsplit=1)
    # deep-link return из ЮKassa: /start paid_<order_id>
    if len(payload) == 2 and payload[1].startswith("paid_"):
        await message.answer(
            "Спасибо! Если вы завершили оплату, откройте заказ "
            "командой /order и нажмите «Я оплатил».",
            reply_markup=main_menu(),
        )
        return
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu())


@router.message(F.text == BTN_BACK)
async def back_to_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(F.text == BTN_FAQ)
async def show_faq(message: Message) -> None:
    await message.answer(format_faq(), reply_markup=main_menu())


@router.message(F.text == BTN_BOOKING)
async def show_booking(message: Message) -> None:
    await message.answer(BOOKING_TEXT, reply_markup=main_menu())


@router.message(F.text == BTN_ABOUT)
async def show_about(message: Message) -> None:
    await message.answer(ABOUT_TEXT, reply_markup=main_menu())


@router.message(F.text == BTN_CONTACT)
async def show_admin_contact(message: Message, config: Config) -> None:
    if not config.admin_telegram and not config.admin_phone:
        await message.answer(CONTACT_UNAVAILABLE_TEXT, reply_markup=main_menu())
        return

    if config.admin_phone:
        await message.answer_contact(
            phone_number=config.admin_phone,
            first_name=config.admin_name,
        )

    await message.answer(
        format_admin_contact_text(
            name=config.admin_name,
            telegram=config.admin_telegram,
            phone=config.admin_phone,
        ),
        reply_markup=main_menu(),
        parse_mode=None,
    )


@router.message(F.text)
async def ai_fallback(
    message: Message,
    deepseek: DeepSeekService,
    cart_service: CartService,
) -> None:
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer(
            "Напишите вопрос текстом или выберите пункт в меню.",
            reply_markup=main_menu(),
        )
        return

    await _ensure_user(message, cart_service)
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )
    user = message.from_user
    telegram_id = user.id if user else message.chat.id
    username = user.username if user else None
    full_name = None
    if user:
        full_name = " ".join(
            part for part in (user.first_name, user.last_name) if part
        ).strip() or None
    answer = await deepseek.reply(
        telegram_id,
        user_text,
        username=username,
        full_name=full_name,
    )
    await message.answer(
        answer,
        reply_markup=main_menu(),
        parse_mode=None,
    )
