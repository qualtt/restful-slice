"""init_orders_tables

Revision ID: 0001_init
Revises: 
Create Date: 2026-05-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id UUID PRIMARY KEY,
            filename TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            uploaded_at TIMESTAMPTZ NOT NULL,
            object_key TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id UUID PRIMARY KEY,
            status TEXT NOT NULL,
            file_id UUID NOT NULL REFERENCES files(file_id) ON DELETE RESTRICT,
            profile_id INTEGER NOT NULL,
            slicing_result JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS orders;")
    op.execute("DROP TABLE IF EXISTS files;")
