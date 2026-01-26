"""Add utm_source to users

Revision ID: 20260126_add_utm_source
Revises: 20260126_add_notification_logs
Create Date: 2026-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260126_add_utm_source'
down_revision = '20260126_add_notification_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add utm_source column to users table
    op.add_column('users', sa.Column('utm_source', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_utm_source'), 'users', ['utm_source'], unique=False)


def downgrade() -> None:
    # Remove utm_source column from users table
    op.drop_index(op.f('ix_users_utm_source'), table_name='users')
    op.drop_column('users', 'utm_source')
