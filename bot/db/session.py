from __future__ import annotations

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.models import Base

_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_path: str) -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker

    directory = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    _engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def create_all() -> None:
    assert _engine is not None, "call init_engine() first"
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    if _engine is not None:
        await _engine.dispose()


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    assert _sessionmaker is not None, "call init_engine() first"
    return _sessionmaker


@asynccontextmanager
async def session_scope():
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
