from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Chat, utcnow
from bot.services import assignments as assignment_service
from bot.services import message_log
from bot.services.keywords import CATEGORIES, DigestMessage, categorize


async def build_daily_digest(session: AsyncSession, chat: Chat, *, now: dt.datetime | None = None) -> str | None:
    """Build the "Итоги дня" digest text for a chat, or None if there's nothing to report."""
    tz = ZoneInfo(chat.timezone)
    now_utc = now or utcnow()
    now_local = now_utc.astimezone(tz)

    start_local = dt.datetime(now_local.year, now_local.month, now_local.day, tzinfo=tz)
    start_utc = start_local.astimezone(dt.timezone.utc)

    messages = await message_log.get_messages_in_range(session, chat.id, start_utc, now_utc)
    closed_today = await assignment_service.get_assignments_due_in_range(session, chat.id, start_utc, now_utc)

    if not messages and not closed_today:
        return None

    lines = [f"\U0001f4d2 Итоги дня — {now_local.strftime('%d.%m.%Y')}", ""]

    active_users = {m.user_id for m in messages}
    lines.append(f"\U0001f4ac Сообщений сегодня: {len(messages)}, активных участников: {len(active_users)}")

    if closed_today:
        lines.append("")
        lines.append("\U0001f4da Домашние задания с дедлайном сегодня:")
        for assignment in closed_today:
            submissions = await assignment_service.get_submissions(session, assignment.id)
            participants = await assignment_service.get_participants(
                session, chat.id, before=assignment.deadline_at
            )
            total = max(len(participants), len(submissions))
            lines.append(f"— «{assignment.title}»: сдали {len(submissions)} из {total}")

    digest_messages = [DigestMessage(display_name=m.display_name, text=m.text) for m in messages]
    picks = categorize(digest_messages)

    rubric_blocks = []
    for category in CATEGORIES:
        pick = picks.get(category.key)
        if pick is None:
            continue
        quote = pick.text.strip()
        rubric_blocks.append(f"{category.emoji} {category.title}:\n«{quote}»\n— {pick.display_name}")

    if rubric_blocks:
        lines.append("")
        lines.append("✨ Рубрика дня")
        lines.append("")
        lines.append("\n\n".join(rubric_blocks))

    return "\n".join(lines)
