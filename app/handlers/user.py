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
    SERVICES_BY_TITLE,
    WELCOME_TEXT,
    format_admin_contact_text,
    format_faq,
    format_service,
    format_services_list,
)
from app.keyboards import (
    BTN_ABOUT,
    BTN_BACK,
    BTN_BOOKING,
    BTN_CONTACT,
    BTN_FAQ,
    BTN_SERVICES,
    main_menu,
    services_menu,
)
from app.services.deepseek import DeepSeekService
from config import Config

router = Router(name="user")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu())


@router.message(F.text == BTN_BACK)
async def back_to_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(F.text == BTN_SERVICES)
async def show_services(message: Message) -> None:
    await message.answer(
        format_services_list(),
        reply_markup=services_menu(),
    )


@router.message(F.text.in_(set(SERVICES_BY_TITLE)))
async def show_service_detail(message: Message) -> None:
    service = SERVICES_BY_TITLE[message.text or ""]
    await message.answer(
        format_service(service),
        reply_markup=services_menu(),
    )


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
async def ai_fallback(message: Message, deepseek: DeepSeekService) -> None:
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer(
            "Напишите вопрос текстом или выберите пункт в меню.",
            reply_markup=main_menu(),
        )
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )
    user_id = message.from_user.id if message.from_user else message.chat.id
    answer = await deepseek.reply(user_id, user_text)
    await message.answer(
        answer,
        reply_markup=main_menu(),
        parse_mode=None,
    )
