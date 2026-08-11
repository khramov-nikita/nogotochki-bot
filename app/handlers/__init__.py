"""Регистрация роутеров."""

from __future__ import annotations

from aiogram import Dispatcher

from . import user


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(user.router)
