from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="common")

HELP_TEXT = (
    "Я слежу за домашками в группе курса осознанности \U0001f9d8\n\n"
    "<b>Для всех участников</b>\n"
    "/deadlines — список активных заданий и дедлайнов\n"
    "/status — моя личная статистика по заданиям\n"
    "(отмечайте выполнение кнопкой «✅ Выполнил(а)» под сообщением с заданием)\n\n"
    "<b>Для кураторов/админов чата</b>\n"
    "/newassignment — создать новое домашнее задание с дедлайном\n"
    "/report &lt;номер&gt; — кто сдал, а кто нет по заданию\n"
    "/cancelassignment &lt;номер&gt; — отменить задание\n"
    "/setdigesttime ЧЧ:ММ — во сколько публиковать «Итоги дня»\n"
    "/settimezone Регион/Город — часовой пояс чата (например Europe/Moscow)\n"
    "/digestnow — собрать и опубликовать дайджест дня прямо сейчас\n\n"
    "⚠️ Чтобы бот видел все сообщения в группе (для дайджеста и учёта участников), "
    "отключите Group Privacy в настройках бота у @BotFather: "
    "/mybots → выбрать бота → Bot Settings → Group Privacy → Turn off."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Добавьте меня в чат курса, сделайте админом и я буду следить за "
        "домашками, дедлайнами и собирать итоги дня.\n\n" + HELP_TEXT
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
