"""Seed new persona shells: milfa, tolstushka

Revision ID: 017
Revises: 016
Create Date: 2026-02-04

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None

NEW_PERSONAS = [
    {
        "key": "milfa",
        "name": "Милфа",
        "short_title": "Милфа (тест)",
        "gender": "female",
        "kind": "SOFT_EMPATH",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "milfa",
        "story_cards": [
            {
                "id": "milfa_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/milfa-story-1.jpeg"
            },
            {
                "id": "milfa_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/milfa-story-2.jpeg"
            },
            {
                "id": "milfa_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/milfa-story-3.jpeg"
            }
        ]
    },
    {
        "key": "tolstushka",
        "name": "Толстушка",
        "short_title": "Толстушка (тест)",
        "gender": "female",
        "kind": "CHAOTIC_FUN",
        "short_description": "Утверждаем",
        "description_short": "Утверждаем",
        "description_long": "Утверждаем",
        "archetype": "tolstushka",
        "story_cards": [
            {
                "id": "tolstushka_1",
                "key": "1",
                "title": "История 1",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/tolstushka-story-1.jpeg"
            },
            {
                "id": "tolstushka_2",
                "key": "2",
                "title": "История 2",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/tolstushka-story-2.jpeg"
            },
            {
                "id": "tolstushka_3",
                "key": "3",
                "title": "История 3",
                "description": "Утверждаем",
                "atmosphere": "flirt_romance",
                "prompt": "Утверждаем",
                "image": "personas/tolstushka-story-3.jpeg"
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
