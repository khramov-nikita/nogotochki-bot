"""Точка входа бота студии «Ноготочки»."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.db import init_db
from app.db.repository import (
    CartRepository,
    DialogRepository,
    OrderRepository,
    UserRepository,
)
from app.handlers import register_routers
from app.services.cart import CartService
from app.services.deepseek import DeepSeekService
from app.services.knowledge_loader import KnowledgeLoadError, load_knowledge_base
from app.services.orders import OrderService
from app.services.payments import MockPaymentClient, YooKassaClient
from app.services.prompts import build_system_prompt
from app.utils.logging import setup_logging
from config import ConfigError, load_config

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Справка"),
    BotCommand(command="services", description="Витрина услуг"),
    BotCommand(command="cart", description="Корзина"),
    BotCommand(command="order", description="Текущий заказ"),
]


async def main() -> None:
    setup_logging()

    try:
        config = load_config()
        knowledge_base = load_knowledge_base()
    except (ConfigError, KnowledgeLoadError) as exc:
        logger.error("%s", exc)
        sys.exit(1)

    db = await init_db(config.db_path)
    users = UserRepository(db)
    dialog = DialogRepository(db)
    cart_repo = CartRepository(db)
    order_repo = OrderRepository(db)

    if config.payments_mock:
        logger.warning(
            "ЮKassa ключи не заданы или PAYMENTS_MOCK=1 — используется мок платежей"
        )
        payments: MockPaymentClient | YooKassaClient = MockPaymentClient()
    else:
        payments = YooKassaClient(
            config.yookassa_shop_id,
            config.yookassa_secret_key,
        )

    cart_service = CartService(users, cart_repo)
    order_service = OrderService(
        cart_repo,
        order_repo,
        payments,
        config.yookassa_return_url,
    )

    system_prompt = build_system_prompt(knowledge_base)
    deepseek = DeepSeekService(config, system_prompt, users, dialog)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(BOT_COMMANDS)

    dp = Dispatcher()
    dp["deepseek"] = deepseek
    dp["config"] = config
    dp["cart_service"] = cart_service
    dp["order_service"] = order_service
    register_routers(dp)

    logger.info("Бот «Ноготочки» запущен (polling), db=%s", config.db_path)
    try:
        await dp.start_polling(bot)
    finally:
        await deepseek.close()
        await payments.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
