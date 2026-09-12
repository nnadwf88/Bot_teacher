from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.assignments import TelegramUser
from bot.services.message_log import record_message

router = Router(name="tracking")

GROUP_TYPES = {"group", "supergroup"}

MIN_TEXT_LENGTH = 3


@router.message(F.chat.type.in_(GROUP_TYPES), F.text, ~F.text.startswith("/"))
async def track_message(message: Message, session: AsyncSession, tg_user: TelegramUser) -> None:
    """Logs plain chat messages so the evening digest can be built from them.

    Registered last so command handlers and the /newassignment FSM steps (handled
    by other routers) take priority and aren't also logged as digest fodder.
    """
    text = message.text or ""
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return
    await record_message(session, message.chat.id, message.message_id, tg_user, text)
