"""Persistence model for tournaments.

This is *not* the domain entity. It is the shape of a database row. Keeping
the two apart is what lets the domain stay a plain frozen dataclass while the
table evolves independently (indexes, denormalisation, soft-delete...).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cleanarch.shared.infrastructure.database import Base


class TournamentModel(Base):
    __tablename__ = "tournaments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phases: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phase_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organizer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optimistic concurrency: every UPDATE is emitted as
    # ``UPDATE ... WHERE id = ? AND version = ?`` and bumps ``version``; if the row
    # changed under us SQLAlchemy raises StaleDataError, which the repository turns
    # into ConflictError. Works on every backend, no locks held between requests.
    # New rows start at 0 (SQLAlchemy's default would be 1) to match the in-memory adapter.
    __mapper_args__ = {  # noqa: RUF012 - SQLAlchemy declarative API
        "version_id_col": version,
        "version_id_generator": lambda current: 0 if current is None else current + 1,
    }
