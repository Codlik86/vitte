"""Add extra_data column to messages table

Revision ID: 20260122_add_message_extra_data
Revises: 20260121_add_dialog_persona_fields
Create Date: 2026-01-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '20260122_add_message_extra_data'
down_revision = '20260121_add_dialog_persona_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add extra_data column to messages table
    op.add_column('messages', sa.Column('extra_data', JSON, nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'extra_data')
