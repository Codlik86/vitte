"""Add broadcasts and broadcast_logs tables

Revision ID: 20260129_add_broadcasts
Revises: 010
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create broadcasts table
    op.create_table(
        'broadcasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('broadcast_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), default='draft', nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('media_url', sa.String(length=512), nullable=True),
        sa.Column('media_type', sa.String(length=16), nullable=True),
        sa.Column('buttons', sa.JSON(), nullable=True),
        sa.Column('gift_images', sa.Integer(), default=0, nullable=False),
        sa.Column('delay_minutes', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_recipients', sa.Integer(), default=0, nullable=False),
        sa.Column('sent_count', sa.Integer(), default=0, nullable=False),
        sa.Column('failed_count', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('celery_task_id', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_broadcasts_id'), 'broadcasts', ['id'], unique=False)
    op.create_index(op.f('ix_broadcasts_status'), 'broadcasts', ['status'], unique=False)
    op.create_index(op.f('ix_broadcasts_broadcast_type'), 'broadcasts', ['broadcast_type'], unique=False)

    # Create broadcast_logs table
    op.create_table(
        'broadcast_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('broadcast_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('success', sa.Boolean(), default=False, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['broadcast_id'], ['broadcasts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_broadcast_logs_id'), 'broadcast_logs', ['id'], unique=False)
    op.create_index(op.f('ix_broadcast_logs_broadcast_id'), 'broadcast_logs', ['broadcast_id'], unique=False)
    op.create_index(op.f('ix_broadcast_logs_user_id'), 'broadcast_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_broadcast_logs_user_id'), table_name='broadcast_logs')
    op.drop_index(op.f('ix_broadcast_logs_broadcast_id'), table_name='broadcast_logs')
    op.drop_index(op.f('ix_broadcast_logs_id'), table_name='broadcast_logs')
    op.drop_table('broadcast_logs')

    op.drop_index(op.f('ix_broadcasts_broadcast_type'), table_name='broadcasts')
    op.drop_index(op.f('ix_broadcasts_status'), table_name='broadcasts')
    op.drop_index(op.f('ix_broadcasts_id'), table_name='broadcasts')
    op.drop_table('broadcasts')
