from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Assignment, Chat, Participant, Submission, utcnow


@dataclass(frozen=True)
class TelegramUser:
    user_id: int
    username: str | None
    full_name: str


async def get_or_create_chat(session: AsyncSession, chat_id: int, title: str, default_timezone: str) -> Chat:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        chat = Chat(id=chat_id, title=title, timezone=default_timezone)
        session.add(chat)
        await session.flush()
    elif title and chat.title != title:
        chat.title = title
    return chat


async def upsert_participant(session: AsyncSession, chat_id: int, user: TelegramUser) -> Participant:
    stmt = select(Participant).where(Participant.chat_id == chat_id, Participant.user_id == user.user_id)
    participant = (await session.execute(stmt)).scalar_one_or_none()
    if participant is None:
        participant = Participant(
            chat_id=chat_id,
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
        )
        session.add(participant)
    else:
        participant.username = user.username
        participant.full_name = user.full_name or participant.full_name
        participant.last_seen_at = utcnow()
    await session.flush()
    return participant


async def get_participants(session: AsyncSession, chat_id: int, *, before: dt.datetime | None = None) -> list[Participant]:
    stmt = select(Participant).where(Participant.chat_id == chat_id)
    if before is not None:
        stmt = stmt.where(Participant.first_seen_at < before)
    return list((await session.execute(stmt)).scalars().all())


async def create_assignment(
    session: AsyncSession,
    *,
    chat_id: int,
    title: str,
    description: str,
    deadline_at: dt.datetime,
    created_by_user_id: int,
) -> Assignment:
    assignment = Assignment(
        chat_id=chat_id,
        title=title,
        description=description,
        deadline_at=deadline_at,
        created_by_user_id=created_by_user_id,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def get_assignment(session: AsyncSession, assignment_id: int) -> Assignment | None:
    return await session.get(Assignment, assignment_id)


async def get_open_assignments(session: AsyncSession, chat_id: int) -> list[Assignment]:
    stmt = (
        select(Assignment)
        .where(Assignment.chat_id == chat_id, Assignment.closed.is_(False), Assignment.cancelled.is_(False))
        .order_by(Assignment.deadline_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_due_assignments(session: AsyncSession, *, now: dt.datetime | None = None) -> list[Assignment]:
    now = now or utcnow()
    stmt = select(Assignment).where(
        Assignment.closed.is_(False),
        Assignment.cancelled.is_(False),
        Assignment.deadline_at <= now,
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_assignments_needing_reminder(
    session: AsyncSession, *, offset: dt.timedelta, field: str, now: dt.datetime | None = None
) -> list[Assignment]:
    """Assignments whose deadline is within `offset` from now and haven't had that reminder sent yet."""
    now = now or utcnow()
    threshold = now + offset
    column = Assignment.reminder1_sent if field == "reminder1_sent" else Assignment.reminder2_sent
    stmt = select(Assignment).where(
        Assignment.closed.is_(False),
        Assignment.cancelled.is_(False),
        column.is_(False),
        Assignment.deadline_at <= threshold,
        Assignment.deadline_at > now,
    )
    return list((await session.execute(stmt)).scalars().all())


async def toggle_submission(session: AsyncSession, assignment: Assignment, user: TelegramUser) -> bool:
    """Mark or unmark an assignment as done for a user. Returns True if now marked done."""
    stmt = select(Submission).where(
        Submission.assignment_id == assignment.id, Submission.user_id == user.user_id
    )
    submission = (await session.execute(stmt)).scalar_one_or_none()
    if submission is None:
        session.add(
            Submission(
                assignment_id=assignment.id,
                user_id=user.user_id,
                username=user.username,
                full_name=user.full_name,
            )
        )
        await session.flush()
        return True
    else:
        await session.delete(submission)
        await session.flush()
        return False


async def get_submissions(session: AsyncSession, assignment_id: int) -> list[Submission]:
    stmt = select(Submission).where(Submission.assignment_id == assignment_id)
    return list((await session.execute(stmt)).scalars().all())


async def get_assignments_due_in_range(
    session: AsyncSession, chat_id: int, start: dt.datetime, end: dt.datetime
) -> list[Assignment]:
    stmt = select(Assignment).where(
        Assignment.chat_id == chat_id,
        Assignment.cancelled.is_(False),
        Assignment.deadline_at >= start,
        Assignment.deadline_at < end,
    )
    return list((await session.execute(stmt)).scalars().all())


async def close_assignment(session: AsyncSession, assignment: Assignment) -> None:
    assignment.closed = True
    await session.flush()


def format_deadline_local(deadline_at: dt.datetime, timezone_name: str) -> str:
    local = deadline_at.astimezone(ZoneInfo(timezone_name))
    return local.strftime("%d.%m.%Y %H:%M")


def format_deadlines_list(assignments: list[Assignment], timezone_name: str) -> str:
    if not assignments:
        return "Активных домашних заданий нет."
    lines = ["📋 Активные задания:"]
    for a in assignments:
        lines.append(f"#{a.id} «{a.title}» — до {format_deadline_local(a.deadline_at, timezone_name)}")
    return "\n".join(lines)


def format_report(
    assignment: Assignment,
    participants: list[Participant],
    submissions: list[Submission],
    timezone_name: str,
) -> str:
    done_ids = {s.user_id for s in submissions}
    done = [s.display_name for s in submissions]
    not_done = [p.display_name for p in participants if p.user_id not in done_ids]

    lines = [
        f"📊 Отчёт по заданию «{assignment.title}» (#{assignment.id})",
        f"Дедлайн: {format_deadline_local(assignment.deadline_at, timezone_name)}",
        "",
        f"✅ Сдали ({len(done)}): " + (", ".join(done) if done else "никто"),
        f"❌ Не сдали ({len(not_done)}): " + (", ".join(not_done) if not_done else "все сдали 🎉"),
    ]
    return "\n".join(lines)
