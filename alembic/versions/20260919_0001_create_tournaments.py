"""create tournaments table (example feature)

Revision ID: 0001
Revises:
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phases", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("phase_index", sa.Integer(), nullable=True),
        sa.Column("round_index", sa.Integer(), nullable=True),
    )
    op.create_index("ix_tournaments_status", "tournaments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tournaments_status", table_name="tournaments")
    op.drop_table("tournaments")
