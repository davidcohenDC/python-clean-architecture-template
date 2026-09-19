"""Value objects describing *how* a tournament is played.

A tournament is a sequence of phases. Each phase is either round-based
(Swiss, round-robin...) or a bracket (single/double elimination), and every
phase after the first must be preceded by a *cut* that selects who advances.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from cleanarch.tournaments.domain.errors import InvalidPhases

MAX_ROUNDS = 20


class PairingSystem(StrEnum):
    SWISS = "swiss"
    ROUND_ROBIN = "round_robin"


class Elimination(StrEnum):
    SINGLE = "single"
    DOUBLE = "double"


@dataclass(frozen=True, slots=True)
class RoundPhase:
    rounds: int
    pairing: PairingSystem = PairingSystem.SWISS

    def __post_init__(self) -> None:
        if not 1 <= self.rounds <= MAX_ROUNDS:
            raise InvalidPhases(f"A round phase needs 1-{MAX_ROUNDS} rounds, got {self.rounds}.")


@dataclass(frozen=True, slots=True)
class BracketPhase:
    elimination: Elimination = Elimination.SINGLE


PhaseConfig = RoundPhase | BracketPhase


@dataclass(frozen=True, slots=True)
class NoCut:
    """Everybody plays this phase (only valid for the first one)."""


@dataclass(frozen=True, slots=True)
class TopCut:
    """Only the best ``players`` advance into this phase."""

    players: int

    def __post_init__(self) -> None:
        if self.players < 2 or self.players & (self.players - 1):
            raise InvalidPhases(f"Top cut must be a power of two >= 2, got {self.players}.")


Cut = NoCut | TopCut


@dataclass(frozen=True, slots=True)
class Phase:
    config: PhaseConfig
    cut: Cut = NoCut()


@dataclass(frozen=True, slots=True)
class Phases(Sequence[Phase]):
    """Ordered, non-empty collection of phases with its invariants enforced once."""

    items: tuple[Phase, ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise InvalidPhases("A tournament needs at least one phase.")
        if not isinstance(self.items[0].cut, NoCut):
            raise InvalidPhases("The first phase cannot have a cut.")
        for index, phase in enumerate(self.items[1:], start=1):
            if isinstance(phase.cut, NoCut):
                raise InvalidPhases(f"Phase {index} must define a cut.")

    @classmethod
    def of(cls, *phases: Phase) -> "Phases":
        return cls(tuple(phases))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[Phase]:
        return iter(self.items)

    def __getitem__(self, index: int) -> Phase:  # type: ignore[override]
        return self.items[index]
