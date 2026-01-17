"""
Database models for Vitte bot
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared.database.base import Base


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
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_interaction = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    dialogs = relationship("Dialog", back_populates="user")

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
