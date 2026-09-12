from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.background.scheduler_loop import run_scheduler_loop
from bot.config import Config
from bot.db.session import create_all, dispose_engine, init_engine
from bot.handlers import assignments, common, digest, tracking
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.registration import EnsureRegisteredMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    config = Config.from_env()
    sessionmaker = init_engine(config.database_path)
    await create_all()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    db_middleware = DbSessionMiddleware(sessionmaker)
    registration_middleware = EnsureRegisteredMiddleware(config)
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(db_middleware)
        observer.outer_middleware(registration_middleware)

    dp.include_router(common.router)
    dp.include_router(assignments.router)
    dp.include_router(digest.router)
    dp.include_router(tracking.router)

    scheduler_task: asyncio.Task | None = None

    async def on_startup() -> None:
        nonlocal scheduler_task
        scheduler_task = asyncio.create_task(run_scheduler_loop(bot, sessionmaker))
        logger.info("Bot started")

    async def on_shutdown() -> None:
        if scheduler_task is not None:
            scheduler_task.cancel()
        await dispose_engine()
        logger.info("Bot stopped")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
