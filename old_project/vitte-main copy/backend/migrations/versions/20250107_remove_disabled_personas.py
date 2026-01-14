"""Remove disabled personas and related data

Revision ID: 20250107_remove_disabled_personas
Revises: 20250107_relationship_level
Create Date: 2025-01-07
"""

from alembic import op

revision = "20250107_remove_disabled_personas"
down_revision = "20250107_relationship_level"
branch_labels = None
depends_on = None


DISABLED_KEYS = (
    "witty_bold_female",
    "chaotic_fun_female",
    "therapeutic_female",
    "anime_waifu_soft_female",
    "anime_tsundere_female",
)


def upgrade():
    conn = op.get_bind()
    conn.execute(
        """
        WITH ids AS (SELECT id FROM personas WHERE key = ANY(:keys))
        DELETE FROM user_personas WHERE persona_id IN (SELECT id FROM ids);
        """,
        {"keys": list(DISABLED_KEYS)},
    )
    conn.execute(
        """
        WITH ids AS (SELECT id FROM personas WHERE key = ANY(:keys))
        DELETE FROM relationship_states WHERE persona_id IN (SELECT id FROM ids);
        """,
        {"keys": list(DISABLED_KEYS)},
    )
    conn.execute(
        """
        WITH ids AS (SELECT id FROM personas WHERE key = ANY(:keys))
        DELETE FROM dialogs WHERE character_id IN (SELECT id FROM ids);
        """,
        {"keys": list(DISABLED_KEYS)},
    )
    conn.execute(
        """
        WITH ids AS (SELECT id FROM personas WHERE key = ANY(:keys))
        DELETE FROM events_personas WHERE persona_id IN (SELECT id FROM ids);
        """,
        {"keys": list(DISABLED_KEYS)},
    )
    conn.execute(
        """
        WITH ids AS (SELECT id FROM personas WHERE key = ANY(:keys))
        DELETE FROM personas WHERE id IN (SELECT id FROM ids);
        """,
        {"keys": list(DISABLED_KEYS)},
    )


def downgrade():
    # Data removal is not reversible
    pass
