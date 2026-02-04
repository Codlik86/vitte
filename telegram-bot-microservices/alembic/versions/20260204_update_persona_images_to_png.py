"""Update persona story card image paths from .jpg to .png

Revision ID: 012
Revises: 011
Create Date: 2026-02-04

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None

# Персонажи с новыми изображениями (Stacy и Yuna не обновляются — папки пустые)
UPDATED_PERSONAS = ['lina', 'marianna', 'mei', 'taya', 'julie', 'ash']


def upgrade() -> None:
    conn = op.get_bind()

    for persona_key in UPDATED_PERSONAS:
        row = conn.execute(
            sa.text("SELECT story_cards FROM personas WHERE key = :key"),
            {"key": persona_key}
        ).fetchone()

        if not row or not row[0]:
            continue

        story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

        for card in story_cards:
            if card.get("image") and card["image"].endswith(".jpg"):
                card["image"] = card["image"][:-4] + ".png"

        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = :key"),
            {"cards": json.dumps(story_cards, ensure_ascii=False), "key": persona_key}
        )


def downgrade() -> None:
    conn = op.get_bind()

    for persona_key in UPDATED_PERSONAS:
        row = conn.execute(
            sa.text("SELECT story_cards FROM personas WHERE key = :key"),
            {"key": persona_key}
        ).fetchone()

        if not row or not row[0]:
            continue

        story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

        for card in story_cards:
            if card.get("image") and card["image"].endswith(".png"):
                card["image"] = card["image"][:-4] + ".jpg"

        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = :key"),
            {"cards": json.dumps(story_cards, ensure_ascii=False), "key": persona_key}
        )
