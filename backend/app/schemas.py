from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StoreProductSchema(BaseModel):
    product_code: str
    title: str
    description: str
    price_stars: int
    type: str


class StoreInfoSchema(BaseModel):
    available_products: list[StoreProductSchema]


class AccessStatusResponse(BaseModel):
    telegram_id: int
    access_status: str
    free_messages_used: int
    free_messages_limit: int
    has_access: bool
    can_send_message: bool
    has_subscription: bool
    is_premium: bool
    plan_code: str | None = None
    premium_until: datetime | None = None
    paywall_variant: str
    store: StoreInfoSchema

class PersonaListItem(BaseModel):
    id: int
    name: str
    short_description: str
    is_default: bool
    is_owner: bool
    is_selected: bool

    class Config:
        orm_mode = True


class PersonaDetails(PersonaListItem):
    long_description: str | None = None
    archetype: str | None = None


class PersonasListResponse(BaseModel):
    items: list[PersonaListItem]


class PersonaCustomCreateRequest(BaseModel):
    telegram_id: int
    name: str
    short_description: str
    vibe: str | None = None  # текст из формы


class ChatRequest(BaseModel):
    telegram_id: int
    message: str


class PaymentPlanSchema(BaseModel):
    code: str
    title: str
    description: str
    price: int
    currency: str
    period: str
    provider: str
    recommended: bool = False


class SubscribeRequest(BaseModel):
    telegram_id: int
    plan_code: str
    provider: str | None = None


class SubscribeResponse(BaseModel):
    subscription_id: int
    provider: str
    status: str
    confirmation: dict[str, Any] | None = None


class StoreProductsResponse(BaseModel):
    products: list[StoreProductSchema]


class StorePurchaseRequest(BaseModel):
    telegram_id: int
    product_code: str


class StorePurchaseResponse(BaseModel):
    purchase_id: int
    provider: str
    status: str
    invoice: dict[str, Any] | None = None


class AnalyticsEventRequest(BaseModel):
    telegram_id: int | None = None
    event_type: str
    payload: dict[str, Any] | None = None
