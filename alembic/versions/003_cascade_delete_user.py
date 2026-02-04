"""add ON DELETE CASCADE to dc_conversations.user_id

Revision ID: 003
Revises: 002
Create Date: 2025-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find and drop existing FK constraint on dc_conversations.user_id
    conn.execute(sa.text("""
        DO $$ 
        DECLARE
            fk_name TEXT;
        BEGIN
            SELECT constraint_name INTO fk_name
            FROM information_schema.table_constraints
            WHERE table_name = 'dc_conversations'
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name IN (
                  SELECT constraint_name
                  FROM information_schema.key_column_usage
                  WHERE table_name = 'dc_conversations'
                    AND column_name = 'user_id'
              );

            IF fk_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE dc_conversations DROP CONSTRAINT ' || fk_name;
            END IF;
        END $$;
    """))

    # Re-create with ON DELETE CASCADE
    conn.execute(sa.text("""
        ALTER TABLE dc_conversations
        ADD CONSTRAINT fk_dc_conversations_user_id
        FOREIGN KEY (user_id) REFERENCES dc_user_profiles(user_id) ON DELETE CASCADE;
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        ALTER TABLE dc_conversations
        DROP CONSTRAINT IF EXISTS fk_dc_conversations_user_id;
    """))

    conn.execute(sa.text("""
        ALTER TABLE dc_conversations
        ADD CONSTRAINT fk_dc_conversations_user_id
        FOREIGN KEY (user_id) REFERENCES dc_user_profiles(user_id);
    """))
