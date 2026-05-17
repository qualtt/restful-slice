"""add files.object_key if missing

Таблица files могла быть создана старым DDL без object_key; CREATE IF NOT EXISTS
в 0001_init не добавляет колонку к уже существующей таблице.

Revision ID: 0003_files_object_key
Revises: 0002_add_telemetry
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_files_object_key"
down_revision: Union[str, None] = "0002_add_telemetry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS object_key TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS object_key;")
