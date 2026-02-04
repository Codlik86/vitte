"""Add image_offset to taya friend and office story cards

Revision ID: 013
Revises: 012
Create Date: 2026-02-04

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None

OFFSET_CARDS = {'taya_friend': '25%', 'taya_office': '25%'}


def upgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT story_cards FROM personas WHERE key = 'taya'")
    ).fetchone()

    if not row or not row[0]:
        return

    story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

    for card in story_cards:
        if card.get("id") in OFFSET_CARDS:
            card["image_offset"] = OFFSET_CARDS[card["id"]]

    conn.execute(
        sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = 'taya'"),
        {"cards": json.dumps(story_cards, ensure_ascii=False)}
    )


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT story_cards FROM personas WHERE key = 'taya'")
    ).fetchone()

    if not row or not row[0]:
        return

    story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

    for card in story_cards:
        card.pop("image_offset", None)

    conn.execute(
        sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = 'taya'"),
        {"cards": json.dumps(story_cards, ensure_ascii=False)}
    )
