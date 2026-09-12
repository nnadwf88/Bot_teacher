from __future__ import annotations

import re
from zoneinfo import ZoneInfoNotFoundError, ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Chat, utcnow
from bot.filters.admin import IsChatAdmin
from bot.services.digest import build_daily_digest

router = Router(name="digest")

GROUP_TYPES = {"group", "supergroup"}
_TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


@router.message(Command("setdigesttime"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_set_digest_time(message: Message, command: CommandObject, session: AsyncSession, chat: Chat) -> None:
    match = _TIME_RE.match(command.args or "")
    if not match:
        await message.answer("Использование: /setdigesttime ЧЧ:ММ, например /setdigesttime 21:00")
        return
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.answer("Некорректное время. Часы 0-23, минуты 0-59.")
        return
    chat.digest_hour = hour
    chat.digest_minute = minute
    await session.flush()
    await message.answer(f"Готово! «Итоги дня» теперь будут публиковаться в {hour:02d}:{minute:02d} ({chat.timezone}).")


@router.message(Command("settimezone"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_set_timezone(message: Message, command: CommandObject, session: AsyncSession, chat: Chat) -> None:
    tz_name = (command.args or "").strip()
    if not tz_name:
        await message.answer("Использование: /settimezone Europe/Moscow")
        return
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        await message.answer(f"Не знаю часовой пояс «{tz_name}». Используйте формат IANA, например Europe/Moscow.")
        return
    chat.timezone = tz_name
    await session.flush()
    await message.answer(f"Часовой пояс чата установлен: {tz_name}")


@router.message(Command("digestnow"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_digest_now(message: Message, session: AsyncSession, chat: Chat) -> None:
    digest_text = await build_daily_digest(session, chat)
    if digest_text is None:
        await message.answer("Пока нечего собирать: за сегодня нет сообщений и закрытых заданий.")
        return
    await message.answer(digest_text)
    chat.last_digest_date = utcnow().astimezone().strftime("%Y-%m-%d")
    await session.flush()
