"""
Database models for Vitte bot
"""
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON, Numeric, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared.database.base import Base


# ==================== ENUMS ====================

class AccessStatus(str, PyEnum):
    NO_ACCESS = "no_access"
    TRIAL_USAGE = "trial_usage"
    SUBSCRIPTION_ACTIVE = "subscription_active"


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


class SubscriptionStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class PurchaseStatus(str, PyEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


# ==================== MODELS ====================

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram user ID
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru")

    # User status
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    has_seen_welcome = Column(Boolean, default=False, nullable=False)

    # Access status for webapp
    access_status = Column(
        String(50),
        default="trial_usage",
        nullable=False
    )
    free_messages_used = Column(Integer, default=0, nullable=False)
    free_messages_limit = Column(Integer, default=10, nullable=False)

    # Active persona
    active_persona_id = Column(Integer, ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_interaction = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    dialogs = relationship("Dialog", back_populates="user")
    active_persona = relationship("Persona", foreign_keys=[active_persona_id])
    image_balance = relationship("ImageBalance", back_populates="user", uselist=False)
    feature_unlocks = relationship("FeatureUnlock", back_populates="user")
    purchases = relationship("Purchase", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Subscription(Base):
    """User subscription model"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    # Subscription details
    plan = Column(String(50), default="free")  # free, premium, enterprise
    is_active = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Limits
    messages_limit = Column(Integer, default=100)
    messages_used = Column(Integer, default=0)
    images_limit = Column(Integer, default=10)
    images_used = Column(Integer, default=0)

    # Upgrades
    intense_mode = Column(Boolean, default=False)
    fantasy_scenes = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan={self.plan})>"


class Dialog(Base):
    """Dialog/conversation model"""
    __tablename__ = "dialogs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Dialog details
    title = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="dialogs")
    messages = relationship("Message", back_populates="dialog")

    def __repr__(self):
        return f"<Dialog(id={self.id}, user_id={self.user_id})>"


class Message(Base):
    """Message model for storing conversation history"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    dialog_id = Column(Integer, ForeignKey("dialogs.id"), nullable=False)
    
    # Message details
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Metadata
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    dialog = relationship("Dialog", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, dialog_id={self.dialog_id}, role={self.role})>"


class Settings(Base):
    """Global settings model"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Settings(key={self.key})>"


class Persona(Base):
    """Persona/character model"""
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    short_title = Column(String(128), nullable=False, default="")
    gender = Column(String(16), nullable=False, default="female")
    kind = Column(
        SAEnum(PersonaKind, name="persona_kind_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=PersonaKind.DEFAULT
    )

    # Descriptions
    short_description = Column(String(255), nullable=True)
    description_short = Column(String(256), nullable=False, default="")
    description_long = Column(Text, nullable=False, default="")
    long_description = Column(Text, nullable=True)

    # Character details
    archetype = Column(String(64), nullable=True)
    system_prompt = Column(Text, nullable=True)
    short_lore = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    emotional_style = Column(Text, nullable=True)
    relationship_style = Column(Text, nullable=True)

    # JSON fields
    style_tags = Column(JSON, nullable=True)
    hooks = Column(JSON, nullable=True)
    triggers_positive = Column(JSON, nullable=True)
    triggers_negative = Column(JSON, nullable=True)
    story_cards = Column(JSON, nullable=True)  # List of story cards

    # Flags
    is_default = Column(Boolean, default=True, nullable=False)
    is_custom = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Custom persona fields
    owner_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    base_persona_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner_user = relationship("User", foreign_keys=[owner_user_id])

    def __repr__(self):
        return f"<Persona(id={self.id}, name={self.name})>"


class UserPersona(Base):
    """User-Persona relationship"""
    __tablename__ = "user_personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    is_owner = Column(Boolean, default=False, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    persona = relationship("Persona")

    def __repr__(self):
        return f"<UserPersona(user_id={self.user_id}, persona_id={self.persona_id})>"


class ImageBalance(Base):
    """User image balance/quota"""
    __tablename__ = "image_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Purchased images
    total_purchased_images = Column(Integer, default=0, nullable=False)
    remaining_purchased_images = Column(Integer, default=0, nullable=False)

    # Daily subscription quota
    daily_subscription_quota = Column(Integer, default=20, nullable=False)
    daily_subscription_used = Column(Integer, default=0, nullable=False)
    daily_quota_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="image_balance")

    def __repr__(self):
        return f"<ImageBalance(user_id={self.user_id})>"


class FeatureUnlock(Base):
    """Unlocked features for user"""
    __tablename__ = "feature_unlocks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_code = Column(String(64), nullable=False, index=True)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="feature_unlocks")

    def __repr__(self):
        return f"<FeatureUnlock(user_id={self.user_id}, feature_code={self.feature_code})>"


class Purchase(Base):
    """Purchase history"""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_code = Column(String(64), nullable=False)
    provider = Column(String(32), nullable=False)  # telegram_stars, yookassa
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(8), nullable=True)
    status = Column(
        SAEnum(PurchaseStatus, name="purchase_status_enum", create_constraint=False, native_enum=False),
        default=PurchaseStatus.PENDING,
        nullable=False
    )
    meta = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="purchases")

    def __repr__(self):
        return f"<Purchase(id={self.id}, user_id={self.user_id}, product_code={self.product_code})>"
