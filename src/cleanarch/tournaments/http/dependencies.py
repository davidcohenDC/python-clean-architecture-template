"""Build use cases from ports, using FastAPI's dependency system.

Only ``get_tournament_repository`` is a placeholder (overridden in
``bootstrap``). Everything else is real code: a use case is just its
constructor applied to its ports.
"""

from typing import Annotated

from fastapi import Depends

from cleanarch.shared.application.ports import EventPublisher
from cleanarch.shared.http.dependencies import get_event_publisher
from cleanarch.tournaments.application import (
    AdvanceTournament,
    CreateTournament,
    GetTournament,
    ListTournaments,
    StartTournament,
    TournamentRepository,
)


def get_tournament_repository() -> TournamentRepository:
    raise NotImplementedError("Provided by cleanarch.bootstrap (dependency_overrides)")


Repository = Annotated[TournamentRepository, Depends(get_tournament_repository)]
Events = Annotated[EventPublisher, Depends(get_event_publisher)]


def create_tournament(repository: Repository, events: Events) -> CreateTournament:
    return CreateTournament(repository, events)


def start_tournament(repository: Repository, events: Events) -> StartTournament:
    return StartTournament(repository, events)


def advance_tournament(repository: Repository, events: Events) -> AdvanceTournament:
    return AdvanceTournament(repository, events)


def get_tournament(repository: Repository) -> GetTournament:
    return GetTournament(repository)


def list_tournaments(repository: Repository) -> ListTournaments:
    return ListTournaments(repository)
