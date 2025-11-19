from pydantic import BaseModel


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
