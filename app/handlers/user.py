"""Хэндлеры пользователя: меню и сценарии из паспорта."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.data.knowledge import (
    ABOUT_TEXT,
    BOOKING_TEXT,
    HELP_TEXT,
    SERVICES_BY_TITLE,
    WELCOME_TEXT,
    format_faq,
    format_service,
    format_services_list,
)
from app.keyboards import (
    BTN_ABOUT,
    BTN_BACK,
    BTN_BOOKING,
    BTN_FAQ,
    BTN_SERVICES,
    main_menu,
    services_menu,
)

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


@router.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Не распознала запрос. Выберите пункт в меню или нажмите /help.",
        reply_markup=main_menu(),
    )
