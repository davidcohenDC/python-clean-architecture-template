from dataclasses import dataclass

from cleanarch.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True)
class TournamentCreated(DomainEvent):
    tournament_id: str
    name: str


@dataclass(frozen=True, slots=True)
class TournamentStarted(DomainEvent):
    tournament_id: str


@dataclass(frozen=True, slots=True)
class TournamentAdvanced(DomainEvent):
    tournament_id: str
    phase_index: int
    round_index: int | None


@dataclass(frozen=True, slots=True)
class TournamentFinished(DomainEvent):
    tournament_id: str
