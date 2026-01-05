import pytest
from fastapi import HTTPException
from starlette.requests import Request
from types import SimpleNamespace

from backend.app.api.miniapp_story_guard import (
    is_miniapp_request,
    require_story_for_miniapp,
    validate_story_for_persona,
)


def _make_request(headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
    }
    return Request(scope)


def test_require_story_for_miniapp_raises_without_story():
    req = _make_request({"X-Telegram-Web-App-Init-Data": "init"})
    with pytest.raises(HTTPException) as exc:
        require_story_for_miniapp(req, None)
    assert exc.value.status_code == 400
    assert exc.value.detail == "story_required"


def test_is_miniapp_request_detects_header():
    req = _make_request({"X-Telegram-Web-App-Init-Data": "init"})
    assert is_miniapp_request(req) is True
    assert is_miniapp_request(_make_request({})) is False


def test_validate_story_for_persona_accepts_known_story():
    persona = SimpleNamespace(archetype="gentle", name="Лина")
    result = validate_story_for_persona(persona, "lina_support")
    assert result == "lina_support"
