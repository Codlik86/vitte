"""Seed new persona shells: uchilka, insta, cosplay, anime1, anime2

Revision ID: 014
Revises: 013
Create Date: 2026-02-04

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None

NEW_PERSONAS = [
    {
        "key": "uchilka",
        "name": "Училка",
        "short_title": "Училка (тест)",
        "gender": "female",
        "kind": "SOFT_EMPATH",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "uchilka",
        "story_cards": [
            {
                "id": "uchilka_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/uchilka-story-1.jpeg"
            },
            {
                "id": "uchilka_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/uchilka-story-2.jpeg"
            },
            {
                "id": "uchilka_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/uchilka-story-3.jpeg"
            }
        ]
    },
    {
        "key": "insta",
        "name": "Инста",
        "short_title": "Инста (тест)",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "insta",
        "story_cards": [
            {
                "id": "insta_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/insta-story-1.jpeg"
            },
            {
                "id": "insta_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/insta-story-2.jpeg"
            },
            {
                "id": "insta_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/insta-story-3.jpeg"
            }
        ]
    },
    {
        "key": "cosplay",
        "name": "Косплей",
        "short_title": "Косплей (тест)",
        "gender": "female",
        "kind": "CHAOTIC_FUN",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "cosplay",
        "story_cards": [
            {
                "id": "cosplay_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/cosplay-story-1.jpeg"
            },
            {
                "id": "cosplay_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/cosplay-story-2.jpeg"
            },
            {
                "id": "cosplay_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/cosplay-story-3.jpeg"
            }
        ]
    },
    {
        "key": "anime1",
        "name": "Аниме 1",
        "short_title": "Аниме 1 (тест)",
        "gender": "female",
        "kind": "ANIME_WAIFU_SOFT",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "anime1",
        "story_cards": [
            {
                "id": "anime1_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime1-story-1.jpeg"
            },
            {
                "id": "anime1_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime1-story-2.jpeg"
            },
            {
                "id": "anime1_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime1-story-3.jpeg"
            }
        ]
    },
    {
        "key": "anime2",
        "name": "Аниме 2",
        "short_title": "Аниме 2 (тест)",
        "gender": "female",
        "kind": "ANIME_WAIFU_SOFT",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "anime2",
        "story_cards": [
            {
                "id": "anime2_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime2-story-1.jpeg"
            },
            {
                "id": "anime2_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime2-story-2.jpeg"
            },
            {
                "id": "anime2_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/anime2-story-3.jpeg"
            }
        ]
    }
]


def upgrade() -> None:
    conn = op.get_bind()

    for p in NEW_PERSONAS:
        conn.execute(
            sa.text("""
                INSERT INTO personas (key, name, short_title, gender, kind, short_description,
                    description_short, description_long, archetype, story_cards,
                    is_default, is_custom, is_active)
                VALUES (:key, :name, :short_title, :gender, :kind, :short_description,
                    :description_short, :description_long, :archetype, CAST(:story_cards AS json),
                    true, false, true)
                ON CONFLICT (key) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_title = EXCLUDED.short_title,
                    short_description = EXCLUDED.short_description,
                    description_short = EXCLUDED.description_short,
                    description_long = EXCLUDED.description_long,
                    story_cards = EXCLUDED.story_cards
            """),
            {
                "key": p["key"],
                "name": p["name"],
                "short_title": p["short_title"],
                "gender": p["gender"],
                "kind": p["kind"],
                "short_description": p["short_description"],
                "description_short": p["description_short"],
                "description_long": p["description_long"],
                "archetype": p["archetype"],
                "story_cards": json.dumps(p["story_cards"], ensure_ascii=False)
            }
        )


def downgrade() -> None:
    conn = op.get_bind()
    for p in NEW_PERSONAS:
        conn.execute(
            sa.text("DELETE FROM personas WHERE key = :key AND is_default = true"),
            {"key": p["key"]}
        )
