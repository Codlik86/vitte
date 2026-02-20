"""Add sex_scene_indices to dialogs

Revision ID: 027
Revises: 026
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('dialogs', sa.Column('sex_scene_indices', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('dialogs', 'sex_scene_indices')
