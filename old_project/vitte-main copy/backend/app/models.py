from datetime import datetime
from enum import Enum as PyEnum
import sqlalchemy as sa
from sqlalchemy import BigInteger, String, Text, ForeignKey, Integer, DateTime, Boolean, Numeric, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PG_ENUM
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
        SAEnum(AccessStatus, name="access_status_enum"),
        default=AccessStatus.TRIAL_USAGE,
        nullable=False,
    )
    free_messages_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paywall_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)
    age_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_adult_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_surprise_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bot_reply_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_image_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
    )
    active_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_persona: Mapped["Persona | None"] = relationship("Persona", foreign_keys=[active_persona_id])

    dialogs: Mapped[list["Dialog"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user")
    image_balance: Mapped["ImageBalance | None"] = relationship("ImageBalance", uselist=False, back_populates="user")
    feature_unlocks: Mapped[list["FeatureUnlock"]] = relationship("FeatureUnlock", back_populates="user")


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    entry_story_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Необходимо создать колонку вручную (Neon): ALTER TABLE dialogs ADD COLUMN IF NOT EXISTS entry_story_id varchar(64);
    last_followup_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remind_1h_sent: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    remind_1d_sent: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    remind_7d_sent: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="dialogs")
    messages: Mapped[list["Message"]] = relationship(back_populates="dialog")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" / "assistant" / "system"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dialog: Mapped["Dialog"] = relationship(back_populates="messages")


class EventAnalytics(Base):
    __tablename__ = "events_analytics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship()


class PersonaKind(str, PyEnum):
    DEFAULT = "DEFAULT"
    SOFT_EMPATH = "SOFT_EMPATH"
    SASSY = "SASSY"
    SMART_COOL = "SMART_COOL"
    CHAOTIC = "CHAOTIC"
    THERAPEUTIC = "THERAPEUTIC"
    ANIME_TSUNDERE = "ANIME_TSUNDERE"
    ANIME_WAIFU_SOFT = "ANIME_WAIFU_SOFT"
    WITTY_BOLD = "WITTY_BOLD"
    CHAOTIC_FUN = "CHAOTIC_FUN"
    CUSTOM = "CUSTOM"


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128))
    short_title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="female", server_default="female")
    kind: Mapped[PersonaKind] = mapped_column(
        SAEnum(
            PersonaKind,
            name="persona_kind_enum",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=PersonaKind.DEFAULT,
        server_default=PersonaKind.DEFAULT.value,
    )
    short_description: Mapped[str] = mapped_column(String(255))
    description_short: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    description_long: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    style_tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text)
    short_lore: Mapped[str | None] = mapped_column(Text, nullable=True)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    legend_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotions_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    hooks: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    triggers_positive: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    triggers_negative: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    base_persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner_user: Mapped["User | None"] = relationship("User", foreign_keys=[owner_user_id])


class PaywallVariant(str, PyEnum):
    A = "A"
    B = "B"


class SubscriptionStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32))
    plan_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status_enum"),
        default=SubscriptionStatus.PENDING,
        nullable=False,
    )
    is_auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    confirmation_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class PurchaseStatus(str, PyEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[PurchaseStatus] = mapped_column(
        SAEnum(PurchaseStatus, name="purchase_status_enum"),
        default=PurchaseStatus.PENDING,
        nullable=False,
    )
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="purchases")


class ImageBalance(Base):
    __tablename__ = "image_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_purchased_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_purchased_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_subscription_quota: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    daily_subscription_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_quota_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="image_balance")


class FeatureUnlock(Base):
    __tablename__ = "feature_unlocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="feature_unlocks")


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


class PersonaEventType(PyEnum):
    CATALOG_OPENED = "persona_catalog_opened"
    PERSONA_SELECTED = "persona_selected"
    PERSONA_CUSTOMIZED = "persona_customized"


class PersonaEvent(Base):
    __tablename__ = "events_personas"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    persona_id = sa.Column(sa.Integer, sa.ForeignKey("personas.id"), nullable=True)
    event_type = sa.Column(
        PG_ENUM(PersonaEventType, name="persona_event_type_enum", create_type=False),
        nullable=False,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    user = sa.orm.relationship("User", backref="persona_events")
    persona = sa.orm.relationship("Persona", backref="persona_events")
