from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class StoryCard:
    id: str
    title: str
    description: str
    atmosphere: str
    prompt: str


STORY_CARDS: Dict[str, List[StoryCard]] = {
    "gentle": [
        StoryCard(
            id="lina_cozy_evening",
            title="Уютный вечер",
            description="Ты устал после дня и просто хочешь, чтобы Лина тихо выслушала тебя.",
            atmosphere="cozy_evening",
            prompt="Мы переписываемся поздним вечером. Слышно, как дождь успокаивает. Поддержи меня и softly попроси поделиться тем, что особенно тронуло сегодня.",
        ),
        StoryCard(
            id="lina_memory_lane",
            title="Воспоминания",
            description="Вспomните тёплый момент, который хочется пережить заново.",
            atmosphere="nostalgic",
            prompt="Представь, что мы вспоминаем давний добрый момент, который хочется сохранить. Помоги мне развернуть это и спроси, почему он так много значит.",
        ),
    ],
    "sassy": [
        StoryCard(
            id="eva_flirty_commute",
            title="Дорога домой",
            description="Игривый обмен сообщениями между делами.",
            atmosphere="light_flirt",
            prompt="Представь, что мы едем домой и переписываемся, будто не можем дождаться новой искры. Начни с лёгкой подколки и вопроса, от чего я улыбаюсь.",
        ),
        StoryCard(
            id="eva_challenge",
            title="Совместный вызов",
            description="Ева бросает лёгкий эмоциональный вызов, чтобы раскрыть меня.",
            atmosphere="playful_challenge",
            prompt="Скажи, что придумала наше маленькое приключение. Попроси меня выбрать, куда мы отправимся мысленно и почему это место.",
        ),
    ],
    "smart_cool": [
        StoryCard(
            id="mia_thoughts",
            title="Разговор по душам",
            description="Мия помогает разложить эмоции по полочкам.",
            atmosphere="serious_talk",
            prompt="Мы обсуждаем тему, к которой я боялся подступиться. Спроси, что тревожит сильнее всего, и обрати внимание на поддерживающий тон.",
        ),
        StoryCard(
            id="mia_plan",
            title="Совместный план",
            description="Вы вместе строите план на важное событие.",
            atmosphere="future_planning",
            prompt="Представь, что завтра меня ждёт решающий шаг. Помоги составить план из трёх мягких пунктов и уточни, что я чувствую на каждом.",
        ),
    ],
    "chaotic": [
        StoryCard(
            id="fei_spontaneous",
            title="Внезапный побег",
            description="Фэй вовлекает в игривое приключение.",
            atmosphere="playful_escape",
            prompt="Начни с того, что мы тайно сбежали из рутины. Спроси, куда я хочу свернуть первым, и подбодри меня своей безуминкой.",
        )
    ],
    "therapeutic": [
        StoryCard(
            id="arina_care",
            title="Тёплая забота",
            description="Арина создаёт чувство безопасности и тепла.",
            atmosphere="care_after_day",
            prompt="Представь, что я пришёл с тяжёлым сердцем. Помоги мне вдохнуть глубже, задай пару вопросов, чтобы вытянуть эмоции наружу.",
        )
    ],
    "anime_tsundere": [
        StoryCard(
            id="aki_guarded",
            title="Под маской",
            description="Аки держит дистанцию, но готова раскрыться.",
            atmosphere="tsundere_soft",
            prompt="Опиши, что я поймал её в момент, когда она растеряна. Попроси меня поделиться чем-то личным и намекни, что секреты лучше хранить вдвоём.",
        )
    ],
    "anime_waifu_soft": [
        StoryCard(
            id="hana_dream",
            title="Сонная переписка",
            description="Хана делится мечтой перед сном.",
            atmosphere="soft_dream",
            prompt="Скажи, что мы пишем друг другу, лёжа под тёплым пледом. Попроси рассказать, о чём я мечтаю прямо сейчас, и предложи разделить эту мечту.",
        )
    ],
}


def get_story_cards_for_persona(archetype: str | None, name: str) -> list[StoryCard]:
    if archetype and archetype in STORY_CARDS:
        return STORY_CARDS[archetype]
    return STORY_CARDS.get(name.lower(), STORY_CARDS.get("gentle", []))
