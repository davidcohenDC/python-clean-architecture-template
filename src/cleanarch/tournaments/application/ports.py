"""Ports owned by the tournament use cases.

The repository is the only feature-specific port. ``EventPublisher`` is shared
(see ``cleanarch.shared.application.ports``). Add a new Protocol here whenever
a use case needs something from the outside world: a clock, an email sender,
a payment gateway... never import the concrete implementation.
"""

from collections.abc import Sequence
from typing import Protocol

from cleanarch.tournaments.domain import Tournament, TournamentId


class TournamentRepository(Protocol):
    """Collection-like access to tournaments. Implemented in ``infrastructure/``."""

    async def add(self, tournament: Tournament) -> None: ...

    async def get(self, tournament_id: TournamentId) -> Tournament | None: ...

    async def save(self, tournament: Tournament) -> Tournament:
        """Persist the new state of an existing tournament and return what is now stored.

        Optimistic concurrency: ``tournament.version`` must match the stored version,
        otherwise ``ConflictError`` is raised and nothing is written. The returned
        aggregate carries the new version.
        """
        ...

    async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]: ...
