"""Deactivate aki persona

Revision ID: 015
Revises: 014
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE personas SET is_active = false WHERE key = 'aki'")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE personas SET is_active = true WHERE key = 'aki'")
    )
