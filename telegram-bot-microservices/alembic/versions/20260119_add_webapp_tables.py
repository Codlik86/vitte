"""Add webapp tables (personas, user_personas, image_balances, feature_unlocks, purchases)

Revision ID: 003
Revises: 002
Create Date: 2026-01-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column(
        'users',
        sa.Column('access_status', sa.String(50), nullable=False, server_default='trial_usage')
    )
    op.add_column(
        'users',
        sa.Column('free_messages_used', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users',
        sa.Column('free_messages_limit', sa.Integer(), nullable=False, server_default='10')
    )
    op.add_column(
        'users',
        sa.Column('active_persona_id', sa.Integer(), nullable=True)
    )

    # Create personas table
    op.create_table(
        'personas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('short_title', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('gender', sa.String(length=16), nullable=False, server_default='female'),
        sa.Column('kind', sa.String(length=50), nullable=False, server_default='DEFAULT'),
        sa.Column('short_description', sa.String(length=255), nullable=True),
        sa.Column('description_short', sa.String(length=256), nullable=False, server_default=''),
        sa.Column('description_long', sa.Text(), nullable=False, server_default=''),
        sa.Column('long_description', sa.Text(), nullable=True),
        sa.Column('archetype', sa.String(length=64), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('short_lore', sa.Text(), nullable=True),
        sa.Column('background', sa.Text(), nullable=True),
        sa.Column('emotional_style', sa.Text(), nullable=True),
        sa.Column('relationship_style', sa.Text(), nullable=True),
        sa.Column('style_tags', sa.JSON(), nullable=True),
        sa.Column('hooks', sa.JSON(), nullable=True),
        sa.Column('triggers_positive', sa.JSON(), nullable=True),
        sa.Column('triggers_negative', sa.JSON(), nullable=True),
        sa.Column('story_cards', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_custom', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('owner_user_id', sa.BigInteger(), nullable=True),
        sa.Column('base_persona_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name='fk_personas_owner_user_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_personas'),
        sa.UniqueConstraint('key', name='uq_personas_key')
    )
    op.create_index('ix_personas_id', 'personas', ['id'])
    op.create_index('ix_personas_key', 'personas', ['key'])

    # Add foreign key from users to personas
    op.create_foreign_key(
        'fk_users_active_persona_id',
        'users', 'personas',
        ['active_persona_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create user_personas table
    op.create_table(
        'user_personas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('is_owner', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_personas_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], name='fk_user_personas_persona_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_user_personas')
    )
    op.create_index('ix_user_personas_id', 'user_personas', ['id'])

    # Create image_balances table
    op.create_table(
        'image_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('total_purchased_images', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('remaining_purchased_images', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_subscription_quota', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('daily_subscription_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_quota_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_image_balances_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_image_balances'),
        sa.UniqueConstraint('user_id', name='uq_image_balances_user_id')
    )
    op.create_index('ix_image_balances_id', 'image_balances', ['id'])

    # Create feature_unlocks table
    op.create_table(
        'feature_unlocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('feature_code', sa.String(length=64), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_feature_unlocks_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_feature_unlocks')
    )
    op.create_index('ix_feature_unlocks_id', 'feature_unlocks', ['id'])
    op.create_index('ix_feature_unlocks_user_id', 'feature_unlocks', ['user_id'])
    op.create_index('ix_feature_unlocks_feature_code', 'feature_unlocks', ['feature_code'])

    # Create purchases table
    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('product_code', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_purchases_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_purchases')
    )
    op.create_index('ix_purchases_id', 'purchases', ['id'])
    op.create_index('ix_purchases_user_id', 'purchases', ['user_id'])


def downgrade() -> None:
    # Drop purchases table
    op.drop_index('ix_purchases_user_id', table_name='purchases')
    op.drop_index('ix_purchases_id', table_name='purchases')
    op.drop_table('purchases')

    # Drop feature_unlocks table
    op.drop_index('ix_feature_unlocks_feature_code', table_name='feature_unlocks')
    op.drop_index('ix_feature_unlocks_user_id', table_name='feature_unlocks')
    op.drop_index('ix_feature_unlocks_id', table_name='feature_unlocks')
    op.drop_table('feature_unlocks')

    # Drop image_balances table
    op.drop_index('ix_image_balances_id', table_name='image_balances')
    op.drop_table('image_balances')

    # Drop user_personas table
    op.drop_index('ix_user_personas_id', table_name='user_personas')
    op.drop_table('user_personas')

    # Drop foreign key from users to personas
    op.drop_constraint('fk_users_active_persona_id', 'users', type_='foreignkey')

    # Drop personas table
    op.drop_index('ix_personas_key', table_name='personas')
    op.drop_index('ix_personas_id', table_name='personas')
    op.drop_table('personas')

    # Drop new columns from users table
    op.drop_column('users', 'active_persona_id')
    op.drop_column('users', 'free_messages_limit')
    op.drop_column('users', 'free_messages_used')
    op.drop_column('users', 'access_status')
