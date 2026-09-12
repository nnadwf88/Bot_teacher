import datetime as dt

from bot.services import assignments as assignment_service
from bot.services import message_log
from bot.services.assignments import TelegramUser
from bot.services.digest import build_daily_digest

CHAT_ID = -100999
ALICE = TelegramUser(user_id=1, username="alice", full_name="Alice")
BOB = TelegramUser(user_id=2, username="bob", full_name="Bob")


async def test_build_daily_digest_none_when_empty(sessionmaker):
    async with sessionmaker() as session:
        chat = await assignment_service.get_or_create_chat(session, CHAT_ID, "Course chat", "Europe/Moscow")
        digest_text = await build_daily_digest(session, chat)
        assert digest_text is None


async def test_build_daily_digest_includes_rubric_and_homework_stats(sessionmaker):
    async with sessionmaker() as session:
        chat = await assignment_service.get_or_create_chat(session, CHAT_ID, "Course chat", "Europe/Moscow")
        await assignment_service.upsert_participant(session, CHAT_ID, ALICE)
        await assignment_service.upsert_participant(session, CHAT_ID, BOB)

        # Deadline must land after the participants were registered (so they still
        # count as "known before the deadline") but before the digest is built.
        deadline_at = dt.datetime.now(dt.timezone.utc)
        await message_log.record_message(
            session, CHAT_ID, 1, ALICE, "Сегодня я поняла, что тревога уходит, если просто дышать."
        )
        await message_log.record_message(session, CHAT_ID, 2, BOB, "Спасибо всем большое за поддержку сегодня!")

        assignment = await assignment_service.create_assignment(
            session,
            chat_id=CHAT_ID,
            title="Практика дыхания",
            description="",
            deadline_at=deadline_at,
            created_by_user_id=ALICE.user_id,
        )
        await assignment_service.toggle_submission(session, assignment, ALICE)

        digest_now = dt.datetime.now(dt.timezone.utc)
        digest_text = await build_daily_digest(session, chat, now=digest_now)

        assert digest_text is not None
        assert "Итоги дня" in digest_text
        assert "Практика дыхания" in digest_text
        assert "сдали 1 из 2" in digest_text
        assert "Инсайт дня" in digest_text
        assert "Благодарность дня" in digest_text
