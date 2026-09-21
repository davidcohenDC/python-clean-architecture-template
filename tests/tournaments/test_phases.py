import pytest

from cleanarch.tournaments.domain import (
    BracketPhase,
    InvalidPhases,
    NoCut,
    Phase,
    Phases,
    RoundPhase,
    TopCut,
)


class TestRoundPhase:
    @pytest.mark.parametrize("rounds", [0, -1, 21])
    def test_rejects_rounds_out_of_range(self, rounds):
        with pytest.raises(InvalidPhases):
            RoundPhase(rounds=rounds)

    def test_accepts_valid_rounds(self):
        assert RoundPhase(rounds=5).rounds == 5


class TestTopCut:
    @pytest.mark.parametrize("players", [0, 1, 3, 6, 100])
    def test_rejects_non_power_of_two(self, players):
        with pytest.raises(InvalidPhases):
            TopCut(players=players)

    @pytest.mark.parametrize("players", [2, 4, 8, 16, 32])
    def test_accepts_powers_of_two(self, players):
        assert TopCut(players=players).players == players


class TestPhases:
    def test_requires_at_least_one_phase(self):
        with pytest.raises(InvalidPhases, match="at least one"):
            Phases.of()

    def test_first_phase_cannot_have_a_cut(self):
        with pytest.raises(InvalidPhases, match="first phase"):
            Phases.of(Phase(RoundPhase(rounds=3), cut=TopCut(players=8)))

    def test_later_phases_must_have_a_cut(self):
        with pytest.raises(InvalidPhases, match="Phase 1 must define a cut"):
            Phases.of(Phase(RoundPhase(rounds=3)), Phase(BracketPhase()))

    def test_valid_sequence_behaves_like_a_sequence(self):
        first, second = Phase(RoundPhase(rounds=3)), Phase(BracketPhase(), cut=TopCut(players=4))
        phases = Phases.of(first, second)

        assert len(phases) == 2
        assert list(phases) == [first, second]
        assert phases[0].cut == NoCut()
        assert phases[1] is second
