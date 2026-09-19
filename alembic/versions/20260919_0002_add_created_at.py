"""add created_at to tournaments (example feature)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Batch mode lets SQLite emulate ALTER TABLE; PostgreSQL runs it natively.
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch.create_index("ix_tournaments_created_at", ["created_at"])
    # The default only backfills existing rows; the application always sets the value.
    with op.batch_alter_table("tournaments") as batch:
        batch.alter_column("created_at", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_index("ix_tournaments_created_at")
        batch.drop_column("created_at")
