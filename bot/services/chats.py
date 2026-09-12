from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Chat


async def get_active_chats(session: AsyncSession) -> list[Chat]:
    stmt = select(Chat).where(Chat.digest_enabled.is_(True))
    return list((await session.execute(stmt)).scalars().all())
