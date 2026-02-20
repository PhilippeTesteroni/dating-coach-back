"""fix dc_training_attempts.status from enum to varchar

Revision ID: 006
Revises: 005
Create Date: 2026-02-20

The attemptstataus enum type causes INSERT errors when SQLAlchemy
uses String(10) for the column. Convert to plain VARCHAR.
Also fixes feedback column from JSONB to TEXT to match current model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert status from enum to varchar
    op.execute(
        "ALTER TABLE dc_training_attempts "
        "ALTER COLUMN status TYPE VARCHAR(10) USING status::text"
    )
    op.execute("DROP TYPE IF EXISTS attemptstataus")

    # Convert feedback from JSONB to TEXT to match current model (stores JSON string)
    op.execute(
        "ALTER TABLE dc_training_attempts "
        "ALTER COLUMN feedback TYPE TEXT USING feedback::text"
    )


def downgrade() -> None:
    # Restore enum (best effort)
    op.execute("CREATE TYPE attemptstataus AS ENUM ('pass', 'fail')")
    op.execute(
        "ALTER TABLE dc_training_attempts "
        "ALTER COLUMN status TYPE attemptstataus USING status::attemptstataus"
    )
    op.execute(
        "ALTER TABLE dc_training_attempts "
        "ALTER COLUMN feedback TYPE JSONB USING feedback::jsonb"
    )
