"""create conversations and messages tables

Revision ID: 002
Revises: 001_create_user_profiles
Create Date: 2025-02-02

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
    conn = op.get_bind()
    
    # Create enum types with IF NOT EXISTS via raw SQL (PostgreSQL anonymous block)
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE actortype AS ENUM ('character', 'coach');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE messagerole AS ENUM ('user', 'assistant');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create conversations table if not exists
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dc_conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES dc_user_profiles(user_id),
            mode_id VARCHAR(50) NOT NULL,
            submode_id VARCHAR(50) NOT NULL,
            actor_type actortype NOT NULL,
            character_id VARCHAR(50),
            difficulty_level INTEGER,
            model_age INTEGER,
            model_orientation VARCHAR(20),
            language VARCHAR(10) DEFAULT 'en',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """))
    
    # Create index if not exists
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_dc_conversations_user_id ON dc_conversations(user_id);
    """))
    
    # Create messages table if not exists
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dc_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES dc_conversations(id) ON DELETE CASCADE,
            role messagerole NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """))
    
    # Create index if not exists
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_dc_messages_conversation_id ON dc_messages(conversation_id);
    """))


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS dc_messages')
    op.execute('DROP TABLE IF EXISTS dc_conversations')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS actortype')
