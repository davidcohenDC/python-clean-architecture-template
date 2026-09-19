"""The ``Tournament`` aggregate root."""

import uuid
from dataclasses import dataclass, field, replace
from typing import NewType

from cleanarch.shared.domain.result import DomainResult
from cleanarch.tournaments.domain.errors import InvalidTournamentName
from cleanarch.tournaments.domain.events import (
    TournamentAdvanced,
    TournamentCreated,
    TournamentFinished,
    TournamentStarted,
)
from cleanarch.tournaments.domain.phases import Phase, Phases
from cleanarch.tournaments.domain.progress import Progress, TournamentStatus

TournamentId = NewType("TournamentId", str)

MAX_NAME_LENGTH = 100


def new_tournament_id() -> TournamentId:
    return TournamentId(uuid.uuid4().hex)


@dataclass(frozen=True, slots=True)
class Tournament:
    id: TournamentId
    name: str
    phases: Phases
    progress: Progress = field(default_factory=Progress)

    def __post_init__(self) -> None:
        if not self.name.strip() or len(self.name) > MAX_NAME_LENGTH:
            raise InvalidTournamentName

    # -- factory ---------------------------------------------------------------
    @classmethod
    def create(
        cls, name: str, phases: Phases, *, id: TournamentId | None = None
    ) -> DomainResult["Tournament"]:
        """Create a new tournament. Use the constructor only to *reconstitute* one."""
        tournament = cls(id=id or new_tournament_id(), name=name, phases=phases)
        return DomainResult.of(tournament, TournamentCreated(tournament.id, tournament.name))

    # -- queries ---------------------------------------------------------------
    @property
    def status(self) -> TournamentStatus:
        return self.progress.status

    @property
    def current_phase(self) -> Phase | None:
        index = self.progress.phase_index
        return None if index is None else self.phases[index]

    # -- commands --------------------------------------------------------------
    def start(self) -> DomainResult["Tournament"]:
        started = replace(self, progress=self.progress.start(self.phases))
        return DomainResult.of(started, TournamentStarted(self.id))

    def advance(self) -> DomainResult["Tournament"]:
        progress = self.progress.advance(self.phases)
        advanced = replace(self, progress=progress)
        if progress.status is TournamentStatus.FINISHED:
            return DomainResult.of(advanced, TournamentFinished(self.id))
        assert progress.phase_index is not None
        return DomainResult.of(
            advanced,
            TournamentAdvanced(self.id, progress.phase_index, progress.round_index),
        )
