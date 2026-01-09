"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-01-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True, server_default='ru'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('is_blocked', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('is_admin', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_interaction', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_users')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=True, server_default='free'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('messages_limit', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('messages_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('images_limit', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('images_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_subscriptions_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_subscriptions'),
        sa.UniqueConstraint('user_id', name='uq_subscriptions_user_id')
    )
    op.create_index('ix_subscriptions_id', 'subscriptions', ['id'])

    # Create dialogs table
    op.create_table(
        'dialogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dialogs_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_dialogs')
    )
    op.create_index('ix_dialogs_id', 'dialogs', ['id'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dialog_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['dialog_id'], ['dialogs.id'], name='fk_messages_dialog_id_dialogs'),
        sa.PrimaryKeyConstraint('id', name='pk_messages')
    )
    op.create_index('ix_messages_id', 'messages', ['id'])

    # Create settings table
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_settings'),
        sa.UniqueConstraint('key', name='uq_settings_key')
    )
    op.create_index('ix_settings_id', 'settings', ['id'])
    op.create_index('ix_settings_key', 'settings', ['key'])


def downgrade() -> None:
    op.drop_index('ix_settings_key', table_name='settings')
    op.drop_index('ix_settings_id', table_name='settings')
    op.drop_table('settings')
    
    op.drop_index('ix_messages_id', table_name='messages')
    op.drop_table('messages')
    
    op.drop_index('ix_dialogs_id', table_name='dialogs')
    op.drop_table('dialogs')
    
    op.drop_index('ix_subscriptions_id', table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
