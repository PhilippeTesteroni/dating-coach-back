"""create dc_user_profiles table

Revision ID: 001
Revises: 
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    gender_enum = postgresql.ENUM('male', 'female', 'other', name='gender', create_type=False)
    preferred_gender_enum = postgresql.ENUM('all', 'male', 'female', name='preferredgender', create_type=False)
    
    gender_enum.create(op.get_bind(), checkfirst=True)
    preferred_gender_enum.create(op.get_bind(), checkfirst=True)
    
    # Create table
    op.create_table(
        'dc_user_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('gender', gender_enum, nullable=True),
        sa.Column('preferred_gender', preferred_gender_enum, server_default='all'),
        sa.Column('age_range_min', sa.Integer(), server_default='18'),
        sa.Column('age_range_max', sa.Integer(), server_default='99'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()')),
    )


def downgrade() -> None:
    op.drop_table('dc_user_profiles')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS preferredgender')
    op.execute('DROP TYPE IF EXISTS gender')
