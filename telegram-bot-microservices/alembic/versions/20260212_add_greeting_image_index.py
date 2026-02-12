"""Add greeting_image_index to dialogs

Revision ID: 026
Revises: 025
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa

revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('dialogs', sa.Column('greeting_image_index', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('dialogs', 'greeting_image_index')
