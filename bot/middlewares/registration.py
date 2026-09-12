from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Chat as TgChat, Message, TelegramObject, User

from bot.config import Config
from bot.services.assignments import TelegramUser, get_or_create_chat, upsert_participant


def _extract_chat_and_user(event: TelegramObject) -> tuple[TgChat | None, User | None]:
    if isinstance(event, Message):
        return event.chat, event.from_user
    if isinstance(event, CallbackQuery) and event.message is not None:
        return event.message.chat, event.from_user
    return None, None


class EnsureRegisteredMiddleware(BaseMiddleware):
    """Registers the chat and the sending user before the handler runs.

    Group membership isn't fully visible via the Bot API, so we treat "has sent at
    least one message" as our definition of a known participant for deadline tracking.
    """

    def __init__(self, config: Config):
        self._config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_chat, tg_user = _extract_chat_and_user(event)
        if tg_chat is not None and tg_chat.type != "private" and tg_user is not None and not tg_user.is_bot:
            session = data["session"]
            chat = await get_or_create_chat(session, tg_chat.id, tg_chat.title or "", self._config.default_timezone)
            user = TelegramUser(
                user_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
            )
            await upsert_participant(session, tg_chat.id, user)
            data["chat"] = chat
            data["tg_user"] = user
        return await handler(event, data)
