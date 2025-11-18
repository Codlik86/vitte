from pydantic import BaseModel


class PersonaBase(BaseModel):
    id: int
    name: str
    short_description: str
    archetype: str | None = None
    is_default: bool
    is_custom: bool
    is_active: bool

    class Config:
        orm_mode = True


class PersonasListResponse(BaseModel):
    items: list[PersonaBase]


class PersonaSelectRequest(BaseModel):
    telegram_id: int
    persona_id: int


class PersonaCustomCreateRequest(BaseModel):
    telegram_id: int
    name: str
    short_description: str
    vibe: str | None = None  # текст из формы


class ChatRequest(BaseModel):
    telegram_id: int
    message: str
