"""add api_key_identity to reservations

Revision ID: 0002_add_api_key_identity
Revises: 0001_init
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_add_api_key_identity"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS api_key_identity TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE reservations DROP COLUMN IF EXISTS api_key_identity;")
