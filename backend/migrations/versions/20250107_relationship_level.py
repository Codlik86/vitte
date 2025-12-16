"""Add relationship_level and manual_override to relationship_states

Revision ID: 20250107_relationship_level
Revises: 
Create Date: 2025-01-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250107_relationship_level"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "relationship_states",
        sa.Column("relationship_level", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "relationship_states",
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )
    op.create_index(
        "ix_relationship_states_level",
        "relationship_states",
        ["relationship_level"],
        unique=False,
    )
    op.create_index(
        "ix_relationship_states_manual_override",
        "relationship_states",
        ["manual_override"],
        unique=False,
    )

    # Backfill levels from existing trust/closeness
    op.execute(
        """
        UPDATE relationship_states
        SET relationship_level = CASE
            WHEN trust_level >= 70 OR closeness_level >= 70 THEN 2
            WHEN trust_level >= 30 OR closeness_level >= 30 THEN 1
            ELSE 0
        END
        """
    )


def downgrade():
    op.drop_index("ix_relationship_states_manual_override", table_name="relationship_states")
    op.drop_index("ix_relationship_states_level", table_name="relationship_states")
    op.drop_column("relationship_states", "manual_override")
    op.drop_column("relationship_states", "relationship_level")
