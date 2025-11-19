from datetime import datetime
from enum import Enum as PyEnum
import enum
import sqlalchemy as sa
from sqlalchemy import BigInteger, String, Text, ForeignKey, Integer, DateTime, Enum, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

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
    active_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_persona: Mapped["Persona | None"] = relationship("Persona", foreign_keys=[active_persona_id])

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


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    short_description: Mapped[str] = mapped_column(String(255))
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text)

    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner_user: Mapped["User | None"] = relationship("User", foreign_keys=[owner_user_id])

class UserPersona(Base):
    __tablename__ = "user_personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    is_owner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    persona: Mapped["Persona"] = relationship("Persona")


class PersonaEventType(enum.Enum):
    CATALOG_OPENED = "persona_catalog_opened"
    PERSONA_SELECTED = "persona_selected"
    PERSONA_CUSTOMIZED = "persona_customized"


class PersonaEvent(Base):
    __tablename__ = "events_personas"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    persona_id = sa.Column(sa.Integer, sa.ForeignKey("personas.id"), nullable=True)
    event_type = sa.Column(
        postgresql.ENUM(PersonaEventType, name="persona_event_type_enum"),
        nullable=False,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    user = sa.orm.relationship("User", backref="persona_events")
    persona = sa.orm.relationship("Persona", backref="persona_events")
