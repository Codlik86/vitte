from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import BigInteger, String, Text, ForeignKey, Integer, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SqlEnum

from .db import Base


class AccessStatus(str, PyEnum):
    NO_ACCESS = "no_access"
    TRIAL_USAGE = "trial_usage"
    SUBSCRIPTION_ACTIVE = "subscription_active"


class PersonaKind(str, PyEnum):
    SOFT_EMPATH = "soft_empath"
    WITTY_BOLD = "witty_bold"
    SMART_COOL = "smart_cool"
    CHAOTIC_FUN = "chaotic_fun"
    THERAPEUTIC = "therapeutic"
    ANIME_TSUNDERE = "anime_tsundere"
    ANIME_YANDERE_SOFT = "anime_yandere_soft"
    ANIME_WAIFU_SOFT = "anime_waifu_soft"


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


class PersonaKind(str, PyEnum):
    SOFT_EMPATH = "soft_empath"
    WITTY_BOLD = "witty_bold"
    SMART_COOL = "smart_cool"
    CHAOTIC_FUN = "chaotic_fun"
    THERAPEUTIC = "therapeutic"
    ANIME_TSUNDERE = "anime_tsundere"
    ANIME_YANDERE_SOFT = "anime_yandere_soft"
    ANIME_WAIFU_SOFT = "anime_waifu_soft"


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    short_title: Mapped[str] = mapped_column(String(128))
    gender: Mapped[str] = mapped_column(String(16))  # "female" / "male" / "nb"
    kind: Mapped[PersonaKind] = mapped_column(
        SqlEnum(PersonaKind, name="persona_kind_enum"),
        nullable=False,
    )
    description_short: Mapped[str] = mapped_column(String(256))
    description_long: Mapped[str] = mapped_column(Text)
    style_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    base_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    base_persona: Mapped["Persona | None"] = relationship(remote_side=[id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])


class UserPersona(Base):
    __tablename__ = "user_personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    persona: Mapped["Persona"] = relationship("Persona")
