"""Add image generation tracking to dialogs

Revision ID: 022
Revises: 021
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa

revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_image_generation_at column to dialogs table."""
    op.add_column(
        'dialogs',
        sa.Column(
            'last_image_generation_at',
            sa.Integer(),
            nullable=True,
            comment='Message count when last image was generated (for trigger frequency tracking)'
        )
    )


def downgrade() -> None:
    """Remove last_image_generation_at column from dialogs table."""
    op.drop_column('dialogs', 'last_image_generation_at')
