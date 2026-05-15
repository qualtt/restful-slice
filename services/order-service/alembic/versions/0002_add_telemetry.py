"""add_telemetry_events_table

Revision ID: 0002_add_telemetry
Revises: 0001_init
Create Date: 2026-05-15 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_telemetry'
down_revision: Union[str, None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_events (
            id UUID PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            route TEXT NOT NULL,
            consent_version TEXT NOT NULL,
            context JSONB NOT NULL,
            data JSONB NOT NULL,
            client_ts TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telemetry_events;")
