"""Shared fixtures and builders.

Each test folder maps to one architectural ring:

    tests/domain        -> cleanarch.*.domain          (pure, no I/O)
    tests/application   -> cleanarch.*.application     (use cases + fakes)
    tests/integration   -> cleanarch.*.infrastructure  (real DB)
    tests/api           -> cleanarch.*.http + bootstrap (HTTP boundary)
    tests/architecture  -> the Dependency Rule itself
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from cleanarch.shared.application.actor import Actor
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.infrastructure.clock import FixedClock

# isort: split
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

# <<< example: tournaments

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
ALICE = Actor("alice")
BOB = Actor("bob")
ADMIN = Actor("root", frozenset({"admin"}))


# >>> example: tournaments
# -- builders: the *only* place tests know how to assemble a valid aggregate ----------


def make_phases(rounds: int = 2, *, with_bracket: bool = True) -> Phases:
    phases = [Phase(RoundPhase(rounds=rounds))]
    if with_bracket:
        phases.append(Phase(BracketPhase(), cut=TopCut(players=8)))
    return Phases.of(*phases)


def make_tournament(
    name: str = "Spring Cup",
    *,
    id: str = "t-1",
    rounds: int = 2,
    with_bracket: bool = True,
    organizer_id: str = "alice",
    created_at: datetime = NOW,
) -> Tournament:
    return Tournament(
        id=TournamentId(id),
        name=name,
        phases=make_phases(rounds, with_bracket=with_bracket),
        organizer_id=organizer_id,
        created_at=created_at,
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


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)
