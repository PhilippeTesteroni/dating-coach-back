"""create dc_subscriptions and dc_message_counters

Revision ID: 004
Revises: 003
Create Date: 2025-02-10

Adds subscription and free-tier message counter tables.
Does NOT touch credits/payment — backward compatible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum type name — must match models.py Enum class name
SUBSCRIPTION_STATUS = postgresql.ENUM(
    'none', 'active', 'expired', 'cancelled',
    name='subscriptionstatus',
    create_type=False,
)


def upgrade() -> None:
    # Create enum type
    SUBSCRIPTION_STATUS.create(op.get_bind(), checkfirst=True)

    # dc_subscriptions
    op.create_table(
        'dc_subscriptions',
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('dc_user_profiles.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('status', SUBSCRIPTION_STATUS, nullable=False, server_default='none'),
        sa.Column('platform', sa.String(20), nullable=True),
        sa.Column('product_id', sa.String(100), nullable=True),
        sa.Column('purchase_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )

    # dc_message_counters
    op.create_table(
        'dc_message_counters',
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('dc_user_profiles.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('dc_message_counters')
    op.drop_table('dc_subscriptions')
    SUBSCRIPTION_STATUS.drop(op.get_bind(), checkfirst=True)
