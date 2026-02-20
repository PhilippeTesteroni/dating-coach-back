"""create dc_training_progress and dc_training_attempts

Revision ID: 005
Revises: 004
Create Date: 2026-02-20

Training progress tracking:
- dc_training_progress: which difficulty levels are unlocked/passed per user
- dc_training_attempts: each evaluation result with feedback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ATTEMPT_STATUS = postgresql.ENUM(
    'pass', 'fail',
    name='attemptstataus',
    create_type=False,
)


def upgrade() -> None:
    ATTEMPT_STATUS.create(op.get_bind(), checkfirst=True)

    # dc_training_progress
    # One row per (user, submode, difficulty_level) combination
    op.create_table(
        'dc_training_progress',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('dc_user_profiles.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('submode_id', sa.String(50), nullable=False),
        sa.Column('difficulty_level', sa.Integer(), nullable=False),  # 1=easy, 2=medium, 3=hard
        sa.Column('is_unlocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('passed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_unique_constraint(
        'uq_training_progress_user_submode_level',
        'dc_training_progress',
        ['user_id', 'submode_id', 'difficulty_level']
    )
    op.create_index('ix_training_progress_user_id', 'dc_training_progress', ['user_id'])

    # dc_training_attempts
    # One row per evaluation (finish button tap)
    op.create_table(
        'dc_training_attempts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('dc_user_profiles.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), sa.ForeignKey('dc_conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('submode_id', sa.String(50), nullable=False),
        sa.Column('difficulty_level', sa.Integer(), nullable=False),
        sa.Column('status', ATTEMPT_STATUS, nullable=False),
        sa.Column('feedback', postgresql.JSONB(), nullable=True),  # {observed: [...], interpretation: [...]}
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_training_attempts_user_id', 'dc_training_attempts', ['user_id'])
    op.create_index('ix_training_attempts_conversation_id', 'dc_training_attempts', ['conversation_id'])


def downgrade() -> None:
    op.drop_index('ix_training_attempts_conversation_id', 'dc_training_attempts')
    op.drop_index('ix_training_attempts_user_id', 'dc_training_attempts')
    op.drop_table('dc_training_attempts')
    op.drop_index('ix_training_progress_user_id', 'dc_training_progress')
    op.drop_table('dc_training_progress')
    ATTEMPT_STATUS.drop(op.get_bind(), checkfirst=True)
