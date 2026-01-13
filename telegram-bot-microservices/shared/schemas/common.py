"""
Common Pydantic schemas for API responses and requests
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema"""
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "ru"


class UserCreate(UserBase):
    """Schema for creating user"""
    pass


class UserResponse(UserBase):
    """Schema for user response"""
    is_active: bool
    is_blocked: bool
    is_admin: bool
    created_at: datetime
    last_interaction: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    """Schema for subscription response"""
    id: int
    user_id: int
    plan: str
    is_active: bool
    messages_limit: int
    messages_used: int
    images_limit: int
    images_used: int
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class DialogResponse(BaseModel):
    """Schema for dialog response"""
    id: int
    user_id: int
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """Schema for creating message"""
    dialog_id: int
    role: str  # user, assistant, system
    content: str


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: int
    dialog_id: int
    role: str
    content: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    service: str
    version: str = "1.0.0"
    timestamp: datetime


# ==================== UPDATE SCHEMAS ====================

class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription"""
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    messages_limit: Optional[int] = None
    images_limit: Optional[int] = None


class DialogUpdate(BaseModel):
    """Schema for updating dialog"""
    title: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== LIST RESPONSES ====================

class DialogListResponse(BaseModel):
    """Schema for list of dialogs"""
    dialogs: list[DialogResponse]
    total: int


class MessageListResponse(BaseModel):
    """Schema for list of messages"""
    messages: list[MessageResponse]
    total: int
    dialog_id: int


# ==================== STATS SCHEMAS ====================

class BotStatsResponse(BaseModel):
    """Schema for bot statistics"""
    total_users: int
    active_users: int
    total_dialogs: int
    total_messages: int
    free_users: int
    premium_users: int
