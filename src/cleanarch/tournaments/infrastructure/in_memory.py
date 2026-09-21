from collections.abc import Sequence
from dataclasses import replace

from cleanarch.shared.application.errors import ConflictError
from cleanarch.tournaments.domain import Tournament, TournamentId


class InMemoryTournamentRepository:
    """Dict-backed repository with the same optimistic-concurrency contract as the SQL one."""

    def __init__(self) -> None:
        self._rows: dict[TournamentId, Tournament] = {}

    async def add(self, tournament: Tournament) -> None:
        self._rows[tournament.id] = replace(tournament, version=0)

    async def get(self, tournament_id: TournamentId) -> Tournament | None:
        return self._rows.get(tournament_id)

    async def save(self, tournament: Tournament) -> Tournament:
        current = self._rows.get(tournament.id)
        if current is None:
            raise LookupError(f"Tournament {tournament.id} does not exist")
        if current.version != tournament.version:
            raise ConflictError(f"Tournament '{tournament.id}' was modified concurrently.")
        saved = replace(tournament, version=tournament.version + 1)
        self._rows[tournament.id] = saved
        return saved

    async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]:
        ordered = sorted(self._rows.values(), key=lambda t: (t.created_at, t.id))
        return ordered[offset : offset + limit]
