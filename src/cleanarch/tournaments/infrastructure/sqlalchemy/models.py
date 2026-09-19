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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
