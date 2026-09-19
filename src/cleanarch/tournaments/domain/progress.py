"""Where a tournament currently is: not started, in a given phase/round, or finished."""

from dataclasses import dataclass, replace
from enum import StrEnum

from cleanarch.tournaments.domain.errors import (
    TournamentAlreadyFinished,
    TournamentAlreadyStarted,
    TournamentNotStarted,
)
from cleanarch.tournaments.domain.phases import Phases, RoundPhase


class TournamentStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class Progress:
    status: TournamentStatus = TournamentStatus.NOT_STARTED
    phase_index: int | None = None
    round_index: int | None = None

    def __post_init__(self) -> None:
        # Not a DomainError: a client can never produce this state through the API,
        # only a corrupted row could. A bug, not a rule violation.
        in_progress = self.status is TournamentStatus.IN_PROGRESS
        if in_progress != (self.phase_index is not None):
            raise ValueError("phase_index must be set if and only if the tournament is in progress")

    def start(self, phases: Phases) -> "Progress":
        if self.status is not TournamentStatus.NOT_STARTED:
            raise TournamentAlreadyStarted
        return self._enter_phase(0, phases)

    def advance(self, phases: Phases) -> "Progress":
        """Move to the next round, or to the next phase, or finish."""
        if self.status is TournamentStatus.NOT_STARTED:
            raise TournamentNotStarted
        if self.status is TournamentStatus.FINISHED:
            raise TournamentAlreadyFinished

        assert self.phase_index is not None
        config = phases[self.phase_index].config
        if isinstance(config, RoundPhase):
            assert self.round_index is not None
            if self.round_index + 1 < config.rounds:
                return replace(self, round_index=self.round_index + 1)

        next_index = self.phase_index + 1
        if next_index >= len(phases):
            return Progress(status=TournamentStatus.FINISHED)
        return self._enter_phase(next_index, phases)

    @staticmethod
    def _enter_phase(index: int, phases: Phases) -> "Progress":
        is_round_phase = isinstance(phases[index].config, RoundPhase)
        return Progress(
            status=TournamentStatus.IN_PROGRESS,
            phase_index=index,
            round_index=0 if is_round_phase else None,
        )
