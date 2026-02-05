"""Fix story_cards image paths: add personas/ prefix

Revision ID: 019
Revises: 018
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa

revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # For each persona, prepend "personas/" to image paths that lack it
    personas = ['lina', 'marianna', 'mei', 'stacey', 'yuna', 'taya', 'julie', 'ash']

    for key in personas:
        conn.execute(
            sa.text("""
                UPDATE personas
                SET story_cards = (
                    SELECT jsonb_agg(
                        CASE
                            WHEN card->>'image' NOT LIKE 'personas/%%'
                            THEN jsonb_set(card, '{image}', to_jsonb('personas/' || (card->>'image')))
                            ELSE card
                        END
                    )
                    FROM jsonb_array_elements(story_cards::jsonb) AS card
                )::json
                WHERE key = :key
            """),
            {"key": key}
        )


def downgrade() -> None:
    conn = op.get_bind()

    personas = ['lina', 'marianna', 'mei', 'stacey', 'yuna', 'taya', 'julie', 'ash']

    for key in personas:
        conn.execute(
            sa.text("""
                UPDATE personas
                SET story_cards = (
                    SELECT jsonb_agg(
                        CASE
                            WHEN card->>'image' LIKE 'personas/%%'
                            THEN jsonb_set(card, '{image}', to_jsonb(substring(card->>'image' FROM 9)))
                            ELSE card
                        END
                    )
                    FROM jsonb_array_elements(story_cards::jsonb) AS card
                )::json
                WHERE key = :key
            """),
            {"key": key}
        )
