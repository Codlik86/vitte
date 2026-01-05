from fastapi import HTTPException, Request

from ..story_cards import get_story_cards_for_persona, resolve_story_id


def is_miniapp_request(request: Request) -> bool:
    header = request.headers.get("X-Telegram-Web-App-Init-Data")
    return bool(header and header.strip())


def require_story_for_miniapp(request: Request, story_id: str | None) -> None:
    if is_miniapp_request(request) and not story_id:
        raise HTTPException(status_code=400, detail="story_required")


def validate_story_for_persona(persona, story_id: str | None) -> str:
    resolved = resolve_story_id(story_id)
    if resolved is None:
        raise HTTPException(status_code=400, detail="story_required")
    cards = get_story_cards_for_persona(getattr(persona, "archetype", None), getattr(persona, "name", ""))
    if resolved not in {card.id for card in cards}:
        raise HTTPException(status_code=400, detail="story_invalid")
    return resolved
