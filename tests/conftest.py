"""Shared fixtures and builders.

Each test folder maps to one architectural ring:

    tests/domain        -> cleanarch.*.domain          (pure, no I/O)
    tests/application   -> cleanarch.*.application     (use cases + fakes)
    tests/integration   -> cleanarch.*.infrastructure  (real DB)
    tests/api           -> cleanarch.*.http + bootstrap (HTTP boundary)
    tests/architecture  -> the Dependency Rule itself
"""

from collections.abc import Sequence

import pytest

from cleanarch.shared.domain.events import DomainEvent

# >>> example: tournaments
from cleanarch.tournaments.domain import (
    BracketPhase,
    Phase,
    Phases,
    RoundPhase,
    TopCut,
    Tournament,
    TournamentId,
)

# -- builders: the *only* place tests know how to assemble a valid aggregate ----------


def make_phases(rounds: int = 2, *, with_bracket: bool = True) -> Phases:
    phases = [Phase(RoundPhase(rounds=rounds))]
    if with_bracket:
        phases.append(Phase(BracketPhase(), cut=TopCut(players=8)))
    return Phases.of(*phases)


def make_tournament(
    name: str = "Spring Cup", *, id: str = "t-1", rounds: int = 2, with_bracket: bool = True
) -> Tournament:
    return Tournament(
        id=TournamentId(id), name=name, phases=make_phases(rounds, with_bracket=with_bracket)
    )


# <<< example: tournaments


# -- fakes -------------------------------------------------------------------------


class RecordingEventPublisher:
    """``EventPublisher`` that remembers what was published. Used by application tests."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        self.events.extend(events)


@pytest.fixture
def events() -> RecordingEventPublisher:
    return RecordingEventPublisher()
