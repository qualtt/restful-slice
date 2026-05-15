"""init_inventory_tables

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
        CREATE TABLE IF NOT EXISTS inventory (
            material_id INTEGER PRIMARY KEY,
            total_grams NUMERIC(12,2) NOT NULL CHECK (total_grams >= 0)
        );

        CREATE TABLE IF NOT EXISTS reservations (
            order_id TEXT PRIMARY KEY,
            reservation_id UUID NOT NULL,
            material_id INTEGER NOT NULL REFERENCES inventory(material_id) ON DELETE RESTRICT,
            amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        INSERT INTO inventory (material_id, total_grams)
        VALUES
            (1, 2500.0),
            (2, 1500.0)
        ON CONFLICT (material_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reservations;")
    op.execute("DROP TABLE IF EXISTS inventory;")
