"""One class per use case, dependencies in the constructor, one ``execute``.

Why classes and not functions? Because a use case is the unit the
composition root wires (``bootstrap/``) and tests instantiate with fakes.
A class with an explicit constructor makes those dependencies visible in one
place. If you prefer functions, ``functools.partial`` gets you the same thing.
"""

from collections.abc import Sequence

from cleanarch.shared.application.actor import Actor
from cleanarch.shared.application.errors import ForbiddenError
from cleanarch.shared.application.ports import Clock, EventPublisher
from cleanarch.tournaments.application.commands import CreateTournamentCommand
from cleanarch.tournaments.application.errors import TournamentNotFound
from cleanarch.tournaments.application.ports import TournamentRepository
from cleanarch.tournaments.domain import Tournament, TournamentId


class CreateTournament:
    def __init__(
        self, repository: TournamentRepository, events: EventPublisher, clock: Clock
    ) -> None:
        self._repository = repository
        self._events = events
        self._clock = clock

    async def execute(self, command: CreateTournamentCommand, actor: Actor) -> Tournament:
        result = Tournament.create(
            name=command.name,
            phases=command.phases,
            organizer_id=actor.id,
            created_at=self._clock.now(),
        )
        await self._repository.add(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate


class StartTournament:
    def __init__(self, repository: TournamentRepository, events: EventPublisher) -> None:
        self._repository = repository
        self._events = events

    async def execute(self, tournament_id: TournamentId, actor: Actor) -> Tournament:
        tournament = await _require(self._repository, tournament_id)
        _authorize(actor, tournament)
        result = tournament.start()
        await self._repository.save(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate


class AdvanceTournament:
    def __init__(self, repository: TournamentRepository, events: EventPublisher) -> None:
        self._repository = repository
        self._events = events

    async def execute(self, tournament_id: TournamentId, actor: Actor) -> Tournament:
        tournament = await _require(self._repository, tournament_id)
        _authorize(actor, tournament)
        result = tournament.advance()
        await self._repository.save(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate


class GetTournament:
    def __init__(self, repository: TournamentRepository) -> None:
        self._repository = repository

    async def execute(self, tournament_id: TournamentId) -> Tournament:
        return await _require(self._repository, tournament_id)


class ListTournaments:
    def __init__(self, repository: TournamentRepository) -> None:
        self._repository = repository

    async def execute(self, *, limit: int = 20, offset: int = 0) -> Sequence[Tournament]:
        return await self._repository.list(limit=limit, offset=offset)


def _authorize(actor: Actor, tournament: Tournament) -> None:
    """Only the organizer (or an admin) runs a tournament. Authorization is an
    application rule: it is about *who asks*, not about the tournament itself."""
    if actor.id != tournament.organizer_id and not actor.is_admin:
        raise ForbiddenError(f"Only the organizer can manage tournament '{tournament.id}'.")


async def _require(repository: TournamentRepository, tournament_id: TournamentId) -> Tournament:
    tournament = await repository.get(tournament_id)
    if tournament is None:
        raise TournamentNotFound(tournament_id)
    return tournament
