import dataclasses

import pytest

from cleanarch.tournaments.domain import (
    InvalidTournamentName,
    Tournament,
    TournamentAdvanced,
    TournamentAlreadyStarted,
    TournamentCreated,
    TournamentFinished,
    TournamentStarted,
    TournamentStatus,
)
from tests.conftest import NOW, make_phases, make_tournament

pytestmark = pytest.mark.domain


class TestCreate:
    def test_generates_an_id_and_emits_created(self):
        result = Tournament.create(
            "Spring Cup", make_phases(), organizer_id="alice", created_at=NOW
        )

        assert result.aggregate.id
        assert result.aggregate.created_at == NOW
        assert result.aggregate.status is TournamentStatus.NOT_STARTED
        assert result.events == (TournamentCreated(result.aggregate.id, "Spring Cup"),)

    @pytest.mark.parametrize("name", ["", "   ", "x" * 101])
    def test_rejects_invalid_names(self, name):
        with pytest.raises(InvalidTournamentName):
            Tournament.create(name, make_phases(), organizer_id="alice", created_at=NOW)


class TestStart:
    def test_returns_new_instance_and_event(self):
        tournament = make_tournament()

        result = tournament.start()

        assert result.aggregate is not tournament, "aggregates are immutable"
        assert tournament.status is TournamentStatus.NOT_STARTED
        assert result.aggregate.status is TournamentStatus.IN_PROGRESS
        assert result.aggregate.current_phase is result.aggregate.phases[0]
        assert result.events == (TournamentStarted(tournament.id),)

    def test_cannot_start_twice(self):
        started = make_tournament().start().aggregate
        with pytest.raises(TournamentAlreadyStarted):
            started.start()


class TestAdvance:
    def test_emits_advanced_with_new_position(self):
        started = make_tournament(rounds=2).start().aggregate

        result = started.advance()

        assert result.events == (TournamentAdvanced(started.id, phase_index=0, round_index=1),)

    def test_emits_finished_after_last_phase(self):
        tournament = make_tournament(rounds=1, with_bracket=False).start().aggregate

        result = tournament.advance()

        assert result.aggregate.status is TournamentStatus.FINISHED
        assert result.aggregate.current_phase is None
        assert result.events == (TournamentFinished(tournament.id),)


def test_is_a_frozen_dataclass():
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_tournament().name = "other"  # type: ignore[misc]
