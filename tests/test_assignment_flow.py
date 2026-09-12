import datetime as dt

from bot.services import assignments as assignment_service
from bot.services.assignments import TelegramUser

CHAT_ID = -100123
ALICE = TelegramUser(user_id=1, username="alice", full_name="Alice")
BOB = TelegramUser(user_id=2, username="bob", full_name="Bob")


async def _setup_chat_with_participants(session):
    chat = await assignment_service.get_or_create_chat(session, CHAT_ID, "Course chat", "Europe/Moscow")
    await assignment_service.upsert_participant(session, CHAT_ID, ALICE)
    await assignment_service.upsert_participant(session, CHAT_ID, BOB)
    return chat


async def test_toggle_submission_marks_and_unmarks(sessionmaker):
    async with sessionmaker() as session:
        await _setup_chat_with_participants(session)
        assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Медитация 10 минут",
            description="",
            deadline_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
            created_by_user_id=ALICE.user_id,
        )

        marked = await assignment_service.toggle_submission(session, assignment, ALICE)
        assert marked is True

        unmarked = await assignment_service.toggle_submission(session, assignment, ALICE)
        assert unmarked is False

        submissions = await assignment_service.get_submissions(session, assignment.id)
        assert submissions == []


async def test_report_lists_who_did_and_did_not(sessionmaker):
    async with sessionmaker() as session:
        await _setup_chat_with_participants(session)
        assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Дневник благодарности",
            description="",
            deadline_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
            created_by_user_id=ALICE.user_id,
        )
        await assignment_service.toggle_submission(session, assignment, ALICE)

        participants = await assignment_service.get_participants(session, CHAT_ID)
        submissions = await assignment_service.get_submissions(session, assignment.id)
        report = assignment_service.format_report(assignment, participants, submissions, "Europe/Moscow")

        assert "@alice" in report
        assert "Сдали (1)" in report
        assert "@bob" in report
        assert "Не сдали (1)" in report


async def test_get_open_assignments_excludes_closed_and_cancelled(sessionmaker):
    async with sessionmaker() as session:
        await _setup_chat_with_participants(session)
        open_assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Открытое",
            description="",
            deadline_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
            created_by_user_id=ALICE.user_id,
        )
        closed_assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Закрытое",
            description="",
            deadline_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
            created_by_user_id=ALICE.user_id,
        )
        await assignment_service.close_assignment(session, closed_assignment)

        cancelled_assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Отменённое",
            description="",
            deadline_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
            created_by_user_id=ALICE.user_id,
        )
        cancelled_assignment.cancelled = True
        await session.flush()

        open_assignments = await assignment_service.get_open_assignments(session, CHAT_ID)
        assert [a.id for a in open_assignments] == [open_assignment.id]
