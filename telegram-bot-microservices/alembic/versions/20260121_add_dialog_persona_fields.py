"""Add persona_id, slot_number, story_id, atmosphere, message_count to dialogs

Revision ID: 007
Revises: 006
Create Date: 2026-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260121_add_dialog_persona_fields'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add persona_id foreign key to dialogs
    op.add_column(
        'dialogs',
        sa.Column('persona_id', sa.Integer(), sa.ForeignKey('personas.id'), nullable=True)
    )

    # Add slot_number for 3-slot dialog system (1, 2, or 3)
    op.add_column(
        'dialogs',
        sa.Column('slot_number', sa.Integer(), nullable=True)
    )

    # Add story_id for current story/scenario
    op.add_column(
        'dialogs',
        sa.Column('story_id', sa.String(64), nullable=True)
    )

    # Add atmosphere for current atmosphere setting
    op.add_column(
        'dialogs',
        sa.Column('atmosphere', sa.String(64), nullable=True)
    )

    # Add message_count for tracking dialog progress
    op.add_column(
        'dialogs',
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0')
    )

    # Create index on user_id + slot_number for fast lookups
    op.create_index(
        'ix_dialogs_user_slot',
        'dialogs',
        ['user_id', 'slot_number'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_dialogs_user_slot', table_name='dialogs')
    op.drop_column('dialogs', 'message_count')
    op.drop_column('dialogs', 'atmosphere')
    op.drop_column('dialogs', 'story_id')
    op.drop_column('dialogs', 'slot_number')
    op.drop_column('dialogs', 'persona_id')
