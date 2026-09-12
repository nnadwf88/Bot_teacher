from __future__ import annotations

import asyncio
import logging
import os
import ssl

import certifi
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.background.scheduler_loop import run_scheduler_loop
from bot.config import Config
from bot.db.session import create_all, dispose_engine, init_engine
from bot.handlers import assignments, common, digest, tracking
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.registration import EnsureRegisteredMiddleware

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class ExtraTrustAiohttpSession(AiohttpSession):
    """AiohttpSession that also trusts one extra CA, for TLS-inspecting proxies."""

    def __init__(self, extra_ca_bundle: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        context = ssl.create_default_context(cafile=certifi.where())
        context.load_verify_locations(cafile=extra_ca_bundle)
        self._connector_init["ssl"] = context


def _build_bot(config: Config) -> Bot:
    session = ExtraTrustAiohttpSession(config.extra_ca_bundle) if config.extra_ca_bundle else None
    return Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def main() -> None:
    config = Config.from_env()
    sessionmaker = init_engine(config.database_path)
    await create_all()

    bot = _build_bot(config)
    dp = Dispatcher(storage=MemoryStorage())

    async def log_every_update(handler, event, data):
        # Metadata only (never message text) — useful to confirm updates are
        # actually arriving without leaking participants' personal reflections
        # into the logs.
        logger.debug("Incoming update #%s: %s", event.update_id, event.event_type)
        return await handler(event, data)

    dp.update.outer_middleware(log_every_update)

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
