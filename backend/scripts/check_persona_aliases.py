#!/usr/bin/env python
"""Simple self-check for persona image config aliases."""

from backend.app.services.persona_images import resolve_persona_key, get_persona_image_config


def main() -> None:
    cases = {
        "Лина": "lina",
        "lina": "lina",
        "Lina": "lina",
        "Мей": "mei",
        "mei": "mei",
        "Mei": "mei",
    }
    for raw, expected in cases.items():
        resolved = resolve_persona_key(raw)
        assert resolved == expected, f"{raw} -> {resolved}, expected {expected}"
        cfg = get_persona_image_config(raw, raw)
        assert cfg.trigger_word, f"{raw} config missing trigger"

    print("ok: persona alias resolution")


if __name__ == "__main__":
    main()
