"""add version to tournaments for optimistic concurrency (example feature)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("tournaments") as batch:
        batch.alter_column("version", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("version")
