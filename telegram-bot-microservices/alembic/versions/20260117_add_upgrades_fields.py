"""Add upgrade fields to subscriptions

Revision ID: 002
Revises: 001
Create Date: 2026-01-17 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add intense_mode column to subscriptions
    op.add_column(
        'subscriptions',
        sa.Column('intense_mode', sa.Boolean(), nullable=True, server_default=sa.text('false'))
    )

    # Add fantasy_scenes column to subscriptions
    op.add_column(
        'subscriptions',
        sa.Column('fantasy_scenes', sa.Boolean(), nullable=True, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'fantasy_scenes')
    op.drop_column('subscriptions', 'intense_mode')
