"""Точка входа бота студии «Ноготочки»."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.handlers import register_routers
from app.utils.logging import setup_logging
from config import ConfigError, load_config

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_routers(dp)

    logger.info("Бот «Ноготочки» запущен (polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
