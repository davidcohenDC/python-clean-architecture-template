"""Builders for the example feature (EXAMPLE - removed with it)."""

from datetime import datetime

from cleanarch.tournaments.domain import (
    BracketPhase,
    Phase,
    Phases,
    RoundPhase,
    TopCut,
    Tournament,
    TournamentId,
)
from tests.conftest import NOW

VALID_PAYLOAD = {
    "name": "Spring Cup",
    "phases": [
        {"config": {"kind": "round", "rounds": 2, "pairing": "swiss"}},
        {"config": {"kind": "bracket", "elimination": "single"}, "cut": {"players": 8}},
    ],
}


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
