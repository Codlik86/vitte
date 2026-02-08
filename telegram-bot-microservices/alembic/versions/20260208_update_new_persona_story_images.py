"""Update new persona story card images from .jpeg to .png

Revision ID: 024
Revises: 023
Create Date: 2026-02-08

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None

# Map: persona_key -> {old_image: new_image}
IMAGE_UPDATES = {
    "anastasia": {
        "personas/anastasia-story-classroom.jpeg": "personas/anastasia-story-classroom.png",
        "personas/anastasia-story-bathroom.jpeg": "personas/anastasia-story-bathroom.png",
    },
    "sasha": {
        "personas/sasha-story-auction.jpeg": "personas/sasha-story-auction.png",
        "personas/sasha-story-plane.jpeg": "personas/sasha-story-plane.png",
        "personas/sasha-story-party.jpeg": "personas/sasha-story-party.png",
    },
    "roxy": {
        "personas/roxy-story-hitchhiker.jpeg": "personas/roxy-story-hitchhiker.png",
        "personas/roxy-story-maid.jpeg": "personas/roxy-story-maid.png",
        "personas/roxy-story-beach.jpeg": "personas/roxy-story-beach.png",
    },
    "pai": {
        "personas/pai-story-dinner.jpeg": "personas/pai-story-dinner.png",
        "personas/pai-story-window.jpeg": "personas/pai-story-window.png",
        "personas/pai-story-car.jpeg": "personas/pai-story-car.png",
    },
    "hani": {
        "personas/hani-story-photoshoot.jpeg": "personas/hani-story-photoshoot.png",
        "personas/hani-story-pool.jpeg": "personas/hani-story-pool.png",
        "personas/hani-story-elevator.jpeg": "personas/hani-story-elevator.png",
    },
}


def upgrade() -> None:
    conn = op.get_bind()

    for persona_key, replacements in IMAGE_UPDATES.items():
        row = conn.execute(
            sa.text("SELECT id, story_cards FROM personas WHERE key = :key"),
            {"key": persona_key}
        ).fetchone()

        if not row:
            continue

        story_cards = row[1] if isinstance(row[1], list) else json.loads(row[1])

        for card in story_cards:
            old_img = card.get("image", "")
            if old_img in replacements:
                card["image"] = replacements[old_img]

        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE id = :id"),
            {"cards": json.dumps(story_cards, ensure_ascii=False), "id": row[0]}
        )


def downgrade() -> None:
    conn = op.get_bind()

    for persona_key, replacements in IMAGE_UPDATES.items():
        # Reverse: new -> old
        reverse = {v: k for k, v in replacements.items()}

        row = conn.execute(
            sa.text("SELECT id, story_cards FROM personas WHERE key = :key"),
            {"key": persona_key}
        ).fetchone()

        if not row:
            continue

        story_cards = row[1] if isinstance(row[1], list) else json.loads(row[1])

        for card in story_cards:
            new_img = card.get("image", "")
            if new_img in reverse:
                card["image"] = reverse[new_img]

        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE id = :id"),
            {"cards": json.dumps(story_cards, ensure_ascii=False), "id": row[0]}
        )
