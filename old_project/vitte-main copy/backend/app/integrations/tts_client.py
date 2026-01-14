from __future__ import annotations

from typing import Any, Dict


async def synthesize_voice(text: str, persona_name: str | None = None) -> Dict[str, Any]:
    """
    Placeholder for future TTS integration.
    Returns a minimal payload so the caller can mark message as voice.
    """
    _ = text  # unused for now
    return {
        "status": "not_implemented",
        "placeholder": "not_implemented_yet",
        "url": None,
        "persona": persona_name,
    }
