"""Swap ash story card images: livingroom <-> bedroom

Revision ID: 016
Revises: 015
Create Date: 2026-02-04

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None

SWAP_MAP = {
    "personas/ash-story-livingroom.png": "personas/ash-story-bedroom.png",
    "personas/ash-story-bedroom.png": "personas/ash-story-livingroom.png",
}


def _swap(direction: dict) -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT story_cards FROM personas WHERE key = 'ash'")
    ).fetchone()

    if not row or not row[0]:
        return

    story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

    for card in story_cards:
        if card.get("image") in direction:
            card["image"] = direction[card["image"]]

    conn.execute(
        sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = 'ash'"),
        {"cards": json.dumps(story_cards, ensure_ascii=False)}
    )


def upgrade() -> None:
    _swap(SWAP_MAP)


def downgrade() -> None:
    _swap(SWAP_MAP)  # swap is its own inverse
