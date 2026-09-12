from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class NewAssignmentStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_deadline = State()
