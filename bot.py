"""Точка входа бота студии «Ноготочки»."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.handlers import register_routers
from app.services.deepseek import DeepSeekService
from app.services.knowledge_loader import KnowledgeLoadError, load_knowledge_base
from app.services.prompts import build_system_prompt
from app.utils.logging import setup_logging
from config import ConfigError, load_config

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    try:
        config = load_config()
        knowledge_base = load_knowledge_base()
    except (ConfigError, KnowledgeLoadError) as exc:
        logger.error("%s", exc)
        sys.exit(1)

    system_prompt = build_system_prompt(knowledge_base)
    deepseek = DeepSeekService(config, system_prompt)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["deepseek"] = deepseek
    dp["config"] = config
    register_routers(dp)

    logger.info("Бот «Ноготочки» запущен (polling)")
    try:
        await dp.start_polling(bot)
    finally:
        await deepseek.close()


if __name__ == "__main__":
    asyncio.run(main())
