from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Chat(Base):
    """A Telegram group chat the bot is running in (one course cohort)."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram chat id
    title: Mapped[str] = mapped_column(String(255), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    digest_hour: Mapped[int] = mapped_column(Integer, default=21)
    digest_minute: Mapped[int] = mapped_column(Integer, default=0)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_digest_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD in chat tz
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    participants: Mapped[list["Participant"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class Participant(Base):
    """A user known to be active in a given chat (has sent at least one message)."""

    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_participant_chat_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.id"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chat: Mapped["Chat"] = relationship(back_populates="participants")

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name or str(self.user_id)


class Assignment(Base):
    """A homework task with a deadline, announced in the chat."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    deadline_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    announce_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reminder1_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 3h before
    reminder2_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 30min before
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)

    chat: Mapped["Chat"] = relationship(back_populates="assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class Submission(Base):
    """A participant marking a given assignment as done."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id", name="uq_submission_assignment_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assignments.id"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name or str(self.user_id)


class DailyMessage(Base):
    """A lightweight log of chat text messages, used for the end-of-day digest.

    Rows older than a retention window are purged after being used for a digest.
    """

    __tablename__ = "daily_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.id"))
    message_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name or str(self.user_id)
