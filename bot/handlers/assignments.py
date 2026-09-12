from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Assignment, Chat
from bot.filters.admin import IsChatAdmin
from bot.services import assignments as assignment_service
from bot.services.assignments import TelegramUser
from bot.services.deadline_parser import DeadlineParseError, parse_deadline
from bot.states import NewAssignmentStates

router = Router(name="assignments")

GROUP_TYPES = {"group", "supergroup"}

SKIP_DESCRIPTION = "нет"


def _done_keyboard(assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Выполнил(а)", callback_data=f"done:{assignment_id}")]]
    )


def _announcement_text(assignment: Assignment, timezone_name: str) -> str:
    deadline = assignment_service.format_deadline_local(assignment.deadline_at, timezone_name)
    text = f"\U0001f4cc <b>Новое задание:</b> {assignment.title}\n"
    if assignment.description:
        text += f"\n{assignment.description}\n"
    text += f"\n⏰ Дедлайн: <b>{deadline}</b>\n\nОтметьтесь кнопкой ниже, когда выполните ✅"
    return text


@router.message(Command("newassignment"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_new_assignment(message: Message, state: FSMContext) -> None:
    await state.set_state(NewAssignmentStates.waiting_title)
    await message.answer(
        "Создаём новое задание. Отправьте <b>название</b> задания (или /cancel для отмены)."
    )


@router.message(Command("cancel"), StateFilter(NewAssignmentStates))
async def cmd_cancel_new_assignment(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Создание задания отменено.")


@router.message(StateFilter(NewAssignmentStates.waiting_title), F.text)
async def new_assignment_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым. Введите название задания.")
        return
    await state.update_data(title=title)
    await state.set_state(NewAssignmentStates.waiting_description)
    await message.answer(f"Теперь отправьте <b>описание</b> задания, или «{SKIP_DESCRIPTION}», чтобы пропустить.")


@router.message(StateFilter(NewAssignmentStates.waiting_description), F.text)
async def new_assignment_description(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    description = "" if text.lower() == SKIP_DESCRIPTION else text
    await state.update_data(description=description)
    await state.set_state(NewAssignmentStates.waiting_deadline)
    await message.answer(
        "Теперь укажите <b>дедлайн</b>. Примеры: «сегодня 21:00», «завтра 09:30», «15.09 20:00»."
    )


@router.message(StateFilter(NewAssignmentStates.waiting_deadline), F.text)
async def new_assignment_deadline(
    message: Message, state: FSMContext, session: AsyncSession, chat: Chat, tg_user: TelegramUser
) -> None:
    try:
        deadline_at = parse_deadline(message.text, chat.timezone)
    except DeadlineParseError as exc:
        await message.answer(str(exc))
        return

    data = await state.get_data()
    assignment = await assignment_service.create_assignment(
        session,
        chat_id=chat.id,
        title=data["title"],
        description=data.get("description", ""),
        deadline_at=deadline_at,
        created_by_user_id=tg_user.user_id,
    )
    await state.clear()

    sent = await message.answer(
        _announcement_text(assignment, chat.timezone), reply_markup=_done_keyboard(assignment.id)
    )
    assignment.announce_message_id = sent.message_id
    await session.flush()


@router.callback_query(F.data.startswith("done:"))
async def on_done_clicked(callback: CallbackQuery, session: AsyncSession, tg_user: TelegramUser) -> None:
    assignment_id = int(callback.data.split(":", 1)[1])
    assignment = await assignment_service.get_assignment(session, assignment_id)
    if assignment is None or assignment.cancelled:
        await callback.answer("Это задание больше не активно.", show_alert=True)
        return
    if assignment.closed:
        await callback.answer("Дедлайн уже прошёл, отметить нельзя.", show_alert=True)
        return

    marked_done = await assignment_service.toggle_submission(session, assignment, tg_user)
    if marked_done:
        await callback.answer("Отмечено как выполненное ✅")
    else:
        await callback.answer("Отметка снята")


@router.message(Command("deadlines"), F.chat.type.in_(GROUP_TYPES))
async def cmd_deadlines(message: Message, session: AsyncSession, chat: Chat) -> None:
    open_assignments = await assignment_service.get_open_assignments(session, chat.id)
    await message.answer(assignment_service.format_deadlines_list(open_assignments, chat.timezone))


@router.message(Command("report"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_report(message: Message, command: CommandObject, session: AsyncSession, chat: Chat) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /report <номер задания>. Номера смотрите в /deadlines.")
        return
    assignment_id = int(command.args.strip())
    assignment = await assignment_service.get_assignment(session, assignment_id)
    if assignment is None or assignment.chat_id != chat.id:
        await message.answer("Задание с таким номером не найдено в этом чате.")
        return

    submissions = await assignment_service.get_submissions(session, assignment.id)
    participants = await assignment_service.get_participants(session, chat.id, before=assignment.deadline_at)
    await message.answer(
        assignment_service.format_report(assignment, participants, submissions, chat.timezone)
    )


@router.message(Command("cancelassignment"), F.chat.type.in_(GROUP_TYPES), IsChatAdmin())
async def cmd_cancel_assignment(message: Message, command: CommandObject, session: AsyncSession, chat: Chat) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /cancelassignment <номер задания>.")
        return
    assignment_id = int(command.args.strip())
    assignment = await assignment_service.get_assignment(session, assignment_id)
    if assignment is None or assignment.chat_id != chat.id:
        await message.answer("Задание с таким номером не найдено в этом чате.")
        return

    assignment.cancelled = True
    await session.flush()
    await message.answer(f"Задание «{assignment.title}» (#{assignment.id}) отменено.")


@router.message(Command("status"), F.chat.type.in_(GROUP_TYPES))
async def cmd_status(message: Message, session: AsyncSession, chat: Chat, tg_user: TelegramUser) -> None:
    open_assignments = await assignment_service.get_open_assignments(session, chat.id)
    if not open_assignments:
        await message.answer("Активных заданий нет.")
        return

    lines = ["Ваш статус по активным заданиям:"]
    for assignment in open_assignments:
        submissions = await assignment_service.get_submissions(session, assignment.id)
        done = any(s.user_id == tg_user.user_id for s in submissions)
        mark = "✅" if done else "❌"
        deadline = assignment_service.format_deadline_local(assignment.deadline_at, chat.timezone)
        lines.append(f"{mark} «{assignment.title}» — до {deadline}")
    await message.answer("\n".join(lines))
