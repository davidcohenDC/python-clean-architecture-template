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
        return list(self._rows.values())[offset : offset + limit]
