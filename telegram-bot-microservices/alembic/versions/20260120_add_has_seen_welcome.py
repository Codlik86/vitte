"""Add has_seen_welcome field to users

Revision ID: 006
Revises: 005
Create Date: 2026-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add has_seen_welcome column to users
    # Default to True for existing users (they've already seen the bot)
    op.add_column(
        'users',
        sa.Column('has_seen_welcome', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )


def downgrade() -> None:
    op.drop_column('users', 'has_seen_welcome')
