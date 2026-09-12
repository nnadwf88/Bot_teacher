from __future__ import annotations

import asyncio
import datetime as dt
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import Chat, utcnow
from bot.services import assignments as assignment_service
from bot.services import message_log
from bot.services.chats import get_active_chats
from bot.services.digest import build_daily_digest

logger = logging.getLogger(__name__)

MESSAGE_RETENTION = dt.timedelta(days=7)

_REMINDERS = (
    (dt.timedelta(hours=3), "reminder1_sent", "⏰ Осталось 3 часа"),
    (dt.timedelta(minutes=30), "reminder2_sent", "⏰ Осталось 30 минут"),
)


async def run_scheduler_loop(bot: Bot, sessionmaker: async_sessionmaker, *, poll_seconds: int = 60) -> None:
    while True:
        try:
            await _tick(bot, sessionmaker)
        except Exception:
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(poll_seconds)


async def _tick(bot: Bot, sessionmaker: async_sessionmaker) -> None:
    async with sessionmaker() as session:
        for offset, field, label in _REMINDERS:
            await _send_reminders(bot, session, offset=offset, field=field, label=label)
        await _close_due_assignments(bot, session)
        await _post_daily_digests(bot, session)
        await session.commit()


async def _send_reminders(bot: Bot, session, *, offset: dt.timedelta, field: str, label: str) -> None:
    due_soon = await assignment_service.get_assignments_needing_reminder(session, offset=offset, field=field)
    for assignment in due_soon:
        participants = await assignment_service.get_participants(
            session, assignment.chat_id, before=assignment.deadline_at
        )
        submissions = await assignment_service.get_submissions(session, assignment.id)
        done_ids = {s.user_id for s in submissions}
        pending = [p for p in participants if p.user_id not in done_ids]

        if pending:
            names = ", ".join(p.display_name for p in pending)
            text = f"{label} до дедлайна задания «{assignment.title}»!\nЕщё не отметились: {names}"
        else:
            text = f"{label} до дедлайна задания «{assignment.title}» — все уже отметились, отлично! \U0001f389"

        try:
            await bot.send_message(assignment.chat_id, text)
        except Exception:
            logger.exception("Failed to send reminder for assignment %s", assignment.id)

        setattr(assignment, field, True)
    if due_soon:
        await session.flush()


async def _close_due_assignments(bot: Bot, session) -> None:
    due = await assignment_service.get_due_assignments(session)
    for assignment in due:
        chat = await session.get(Chat, assignment.chat_id)
        timezone_name = chat.timezone if chat else "UTC"
        participants = await assignment_service.get_participants(
            session, assignment.chat_id, before=assignment.deadline_at
        )
        submissions = await assignment_service.get_submissions(session, assignment.id)
        report = assignment_service.format_report(assignment, participants, submissions, timezone_name)

        try:
            await bot.send_message(assignment.chat_id, "⌛ Дедлайн наступил!\n\n" + report)
        except Exception:
            logger.exception("Failed to send closing report for assignment %s", assignment.id)

        await assignment_service.close_assignment(session, assignment)


async def _post_daily_digests(bot: Bot, session) -> None:
    now_utc = utcnow()
    purged = False
    for chat in await get_active_chats(session):
        tz = ZoneInfo(chat.timezone)
        now_local = now_utc.astimezone(tz)
        today_str = now_local.strftime("%Y-%m-%d")
        if chat.last_digest_date == today_str:
            continue
        if now_local.time() < dt.time(chat.digest_hour, chat.digest_minute):
            continue

        digest_text = await build_daily_digest(session, chat, now=now_utc)
        if digest_text is not None:
            try:
                await bot.send_message(chat.id, digest_text)
            except Exception:
                logger.exception("Failed to send digest for chat %s", chat.id)
        chat.last_digest_date = today_str

        if not purged:
            await message_log.purge_messages_older_than(session, now_utc - MESSAGE_RETENTION)
            purged = True
