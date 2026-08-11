"""Регистрация роутеров."""

from __future__ import annotations

from aiogram import Dispatcher

from . import cart, orders, user


def register_routers(dp: Dispatcher) -> None:
    # Сначала корзина/заказы, затем общее меню и AI-fallback
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(user.router)
