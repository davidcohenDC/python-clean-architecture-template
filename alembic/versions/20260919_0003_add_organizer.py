"""add organizer_id to tournaments (example feature)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(
            sa.Column("organizer_id", sa.String(64), nullable=False, server_default="anonymous")
        )
        batch.create_index("ix_tournaments_organizer_id", ["organizer_id"])
    with op.batch_alter_table("tournaments") as batch:
        batch.alter_column("organizer_id", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_index("ix_tournaments_organizer_id")
        batch.drop_column("organizer_id")
