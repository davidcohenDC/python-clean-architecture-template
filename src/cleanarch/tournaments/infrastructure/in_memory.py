from collections.abc import Sequence

from cleanarch.tournaments.domain import Tournament, TournamentId


class InMemoryTournamentRepository:
    """Dict-backed repository. Immutable aggregates make this trivially safe."""

    def __init__(self) -> None:
        self._rows: dict[TournamentId, Tournament] = {}

    async def add(self, tournament: Tournament) -> None:
        self._rows[tournament.id] = tournament

    async def get(self, tournament_id: TournamentId) -> Tournament | None:
        return self._rows.get(tournament_id)

    async def save(self, tournament: Tournament) -> None:
        self._rows[tournament.id] = tournament

    async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]:
        ordered = sorted(self._rows.values(), key=lambda t: (t.created_at, t.id))
        return ordered[offset : offset + limit]
