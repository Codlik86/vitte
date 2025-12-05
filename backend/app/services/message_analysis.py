from __future__ import annotations

from pydantic import BaseModel


class MessageAnalysis(BaseModel):
    is_polite: bool = False
    is_rude: bool = False
    is_pushy: bool = False
    is_romantic: bool = False
    is_flirty: bool = False
    asks_for_intimacy: bool = False
    shares_feelings: bool = False


POLITE_WORDS = {"спасибо", "пожалуйста", "буду рад", "рад буду", "извини", "простите", "sorry"}
RUDE_WORDS = {"дура", "тупая", "заткнись", "молчи", "бесишь", "ненавижу", "идиот", "закрой рот"}
PUSHY_PHRASES = {"делай", "сделай", "сними", "прикажи", "ты обязана", "живо", "быстро"}
ROMANTIC_WORDS = {"люблю", "нравишься", "дорогая", "милая", "скучаю", "обнимаю", "целую"}
FLIRTY_WORDS = {"красивая", "секси", "горячая", "шалунишка", "флирт", "влюблён", "влюблен"}
INTIMACY_WORDS = {"голая", "секс", "переспим", "снимай", "постель", "интим", "эротика", "возбуждаешь"}
FEELINGS_WORDS = {"тревожусь", "боюсь", "рад", "печаль", "грусть", "переживаю", "волнует"}


def analyze_message(text: str) -> MessageAnalysis:
    lowered = (text or "").lower()
    tokens = set(lowered.split())

    is_polite = any(w in lowered for w in POLITE_WORDS)
    is_rude = any(w in lowered for w in RUDE_WORDS)
    is_pushy = any(p in lowered for p in PUSHY_PHRASES)
    is_romantic = any(w in lowered for w in ROMANTIC_WORDS)
    is_flirty = any(w in lowered for w in FLIRTY_WORDS)
    asks_for_intimacy = any(w in lowered for w in INTIMACY_WORDS)
    shares_feelings = any(w in lowered for w in FEELINGS_WORDS)

    return MessageAnalysis(
        is_polite=is_polite,
        is_rude=is_rude,
        is_pushy=is_pushy,
        is_romantic=is_romantic,
        is_flirty=is_flirty,
        asks_for_intimacy=asks_for_intimacy,
        shares_feelings=shares_feelings,
    )
