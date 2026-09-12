import datetime as dt

from bot.services import assignments as assignment_service
from bot.services.assignments import TelegramUser

CHAT_ID = -100777
ALICE = TelegramUser(user_id=1, username="alice", full_name="Alice")


async def test_get_due_assignments_only_returns_past_deadlines(sessionmaker):
    async with sessionmaker() as session:
        await assignment_service.get_or_create_chat(session, CHAT_ID, "Chat", "Europe/Moscow")
        now = dt.datetime.now(dt.timezone.utc)

        past = await assignment_service.create_assignment(
            session, chat_id=CHAT_ID, title="Past", description="",
            deadline_at=now - dt.timedelta(minutes=5), created_by_user_id=ALICE.user_id,
        )
        future = await assignment_service.create_assignment(
            session, chat_id=CHAT_ID, title="Future", description="",
            deadline_at=now + dt.timedelta(hours=5), created_by_user_id=ALICE.user_id,
        )

        due = await assignment_service.get_due_assignments(session, now=now)
        assert [a.id for a in due] == [past.id]
        assert future.id not in [a.id for a in due]


async def test_get_assignments_needing_reminder_respects_window_and_flag(sessionmaker):
    async with sessionmaker() as session:
        await assignment_service.get_or_create_chat(session, CHAT_ID, "Chat", "Europe/Moscow")
        now = dt.datetime.now(dt.timezone.utc)

        soon = await assignment_service.create_assignment(
            session, chat_id=CHAT_ID, title="Soon", description="",
            deadline_at=now + dt.timedelta(minutes=20), created_by_user_id=ALICE.user_id,
        )
        far = await assignment_service.create_assignment(
            session, chat_id=CHAT_ID, title="Far", description="",
            deadline_at=now + dt.timedelta(hours=5), created_by_user_id=ALICE.user_id,
        )

        needing = await assignment_service.get_assignments_needing_reminder(
            session, offset=dt.timedelta(minutes=30), field="reminder2_sent", now=now
        )
        assert [a.id for a in needing] == [soon.id]
        assert far.id not in [a.id for a in needing]

        soon.reminder2_sent = True
        await session.flush()

        needing_after_flag = await assignment_service.get_assignments_needing_reminder(
            session, offset=dt.timedelta(minutes=30), field="reminder2_sent", now=now
        )
        assert needing_after_flag == []
