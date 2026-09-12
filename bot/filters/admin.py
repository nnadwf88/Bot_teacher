from __future__ import annotations

from aiogram import Bot
from aiogram.filters import Filter
from aiogram.types import Message


class IsChatAdmin(Filter):
    """Passes only for messages sent by a chat administrator/creator, or in a private chat."""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        if message.chat.type == "private":
            return True
        if message.from_user is None:
            return False
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
