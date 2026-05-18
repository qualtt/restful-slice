"""add api_key_identity columns

Revision ID: 0004_add_api_key_identity
Revises: 0003_files_object_key
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_add_api_key_identity"
down_revision: Union[str, None] = "0003_files_object_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS api_key_identity TEXT;")
    op.execute("ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS api_key_identity TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE telemetry_events DROP COLUMN IF EXISTS api_key_identity;")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS api_key_identity;")
