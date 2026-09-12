from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import DailyMessage
from bot.services.assignments import TelegramUser


async def record_message(
    session: AsyncSession, chat_id: int, message_id: int, user: TelegramUser, text: str
) -> None:
    session.add(
        DailyMessage(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            text=text,
        )
    )
    await session.flush()


async def get_messages_in_range(
    session: AsyncSession, chat_id: int, start: dt.datetime, end: dt.datetime
) -> list[DailyMessage]:
    stmt = select(DailyMessage).where(
        DailyMessage.chat_id == chat_id,
        DailyMessage.sent_at >= start,
        DailyMessage.sent_at < end,
    )
    return list((await session.execute(stmt)).scalars().all())


async def purge_messages_older_than(session: AsyncSession, cutoff: dt.datetime) -> int:
    result = await session.execute(delete(DailyMessage).where(DailyMessage.sent_at < cutoff))
    await session.flush()
    return result.rowcount or 0
