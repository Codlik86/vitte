from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import BigInteger, String, Text, ForeignKey, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class AccessStatus(str, PyEnum):
    NO_ACCESS = "no_access"
    TRIAL_USAGE = "trial_usage"
    SUBSCRIPTION_ACTIVE = "subscription_active"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    access_status: Mapped[AccessStatus] = mapped_column(
        Enum(AccessStatus, name="access_status_enum"),
        default=AccessStatus.TRIAL_USAGE,
        nullable=False,
    )
    free_messages_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    dialogs: Mapped[list["Dialog"]] = relationship(back_populates="user")


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    character_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="dialogs")
    messages: Mapped[list["Message"]] = relationship(back_populates="dialog")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # "user" / "assistant" / "system"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dialog: Mapped["Dialog"] = relationship(back_populates="messages")


class EventAnalytics(Base):
    __tablename__ = "events_analytics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship()
