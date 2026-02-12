"""Update Julie bus_fun story to 'Вечер в комнате'

Revision ID: 025
Revises: 024
Create Date: 2026-02-11

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None

OLD_TITLE = "Развлечения в автобусе"
OLD_DESC = "Джули едет в переполненном автобусе. Ты стоишь рядом. Она начинает игру с намёками."

NEW_TITLE = "Вечер в комнате"
NEW_DESC = "В общежитии уже тихо, большинство разошлись по комнатам. Джули осталась у тебя — немного смущённая, но любопытная."


def upgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT id, story_cards FROM personas WHERE key = :key"),
        {"key": "julie"}
    ).fetchone()

    if not row:
        return

    story_cards = row[1] if isinstance(row[1], list) else json.loads(row[1])

    for card in story_cards:
        if card.get("key") == "bus_fun":
            card["title"] = NEW_TITLE
            card["description"] = NEW_DESC

    conn.execute(
        sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE id = :id"),
        {"cards": json.dumps(story_cards, ensure_ascii=False), "id": row[0]}
    )


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT id, story_cards FROM personas WHERE key = :key"),
        {"key": "julie"}
    ).fetchone()

    if not row:
        return

    story_cards = row[1] if isinstance(row[1], list) else json.loads(row[1])

    for card in story_cards:
        if card.get("key") == "bus_fun":
            card["title"] = OLD_TITLE
            card["description"] = OLD_DESC

    conn.execute(
        sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE id = :id"),
        {"cards": json.dumps(story_cards, ensure_ascii=False), "id": row[0]}
    )
