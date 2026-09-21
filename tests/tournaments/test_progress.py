import pytest

from cleanarch.tournaments.domain import (
    Progress,
    TournamentAlreadyFinished,
    TournamentAlreadyStarted,
    TournamentNotStarted,
    TournamentStatus,
)
from tests.tournaments.conftest import make_phases

pytestmark = pytest.mark.domain


def test_initial_state_is_not_started():
    progress = Progress()
    assert progress.status is TournamentStatus.NOT_STARTED
    assert progress.phase_index is None
    assert progress.round_index is None


def test_in_progress_requires_a_phase_index():
    with pytest.raises(ValueError):
        Progress(status=TournamentStatus.IN_PROGRESS)
    with pytest.raises(ValueError):
        Progress(status=TournamentStatus.NOT_STARTED, phase_index=0)


def test_start_enters_first_phase_at_round_zero():
    progress = Progress().start(make_phases(rounds=3))
    assert progress == Progress(TournamentStatus.IN_PROGRESS, phase_index=0, round_index=0)


def test_cannot_start_twice():
    phases = make_phases()
    with pytest.raises(TournamentAlreadyStarted):
        Progress().start(phases).start(phases)


def test_cannot_advance_before_start():
    with pytest.raises(TournamentNotStarted):
        Progress().advance(make_phases())


def test_advance_walks_rounds_then_phases_then_finishes():
    phases = make_phases(rounds=2, with_bracket=True)
    progress = Progress().start(phases)

    progress = progress.advance(phases)
    assert (progress.phase_index, progress.round_index) == (0, 1)

    progress = progress.advance(phases)  # bracket phase: no rounds
    assert (progress.phase_index, progress.round_index) == (1, None)

    progress = progress.advance(phases)
    assert progress.status is TournamentStatus.FINISHED
    assert progress.phase_index is None


def test_cannot_advance_when_finished():
    phases = make_phases(rounds=1, with_bracket=False)
    finished = Progress().start(phases).advance(phases)
    assert finished.status is TournamentStatus.FINISHED
    with pytest.raises(TournamentAlreadyFinished):
        finished.advance(phases)
