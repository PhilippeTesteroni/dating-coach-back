"""create conversations and messages tables

Revision ID: 002
Revises: 001_create_user_profiles
Create Date: 2025-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    actor_type = postgresql.ENUM('character', 'coach', name='actortype', create_type=False)
    actor_type.create(op.get_bind(), checkfirst=True)
    
    message_role = postgresql.ENUM('user', 'assistant', name='messagerole', create_type=False)
    message_role.create(op.get_bind(), checkfirst=True)
    
    # Create conversations table
    op.create_table(
        'dc_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mode_id', sa.String(50), nullable=False),
        sa.Column('submode_id', sa.String(50), nullable=False),
        sa.Column('actor_type', sa.Enum('character', 'coach', name='actortype'), nullable=False),
        sa.Column('character_id', sa.String(50), nullable=True),
        sa.Column('difficulty_level', sa.Integer(), nullable=True),
        sa.Column('model_age', sa.Integer(), nullable=True),
        sa.Column('model_orientation', sa.String(20), nullable=True),
        sa.Column('language', sa.String(10), server_default='en', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['dc_user_profiles.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on user_id for listing conversations
    op.create_index('ix_dc_conversations_user_id', 'dc_conversations', ['user_id'])
    
    # Create messages table
    op.create_table(
        'dc_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['dc_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on conversation_id for fetching messages
    op.create_index('ix_dc_messages_conversation_id', 'dc_messages', ['conversation_id'])


def downgrade() -> None:
    op.drop_index('ix_dc_messages_conversation_id', table_name='dc_messages')
    op.drop_table('dc_messages')
    op.drop_index('ix_dc_conversations_user_id', table_name='dc_conversations')
    op.drop_table('dc_conversations')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS actortype')
