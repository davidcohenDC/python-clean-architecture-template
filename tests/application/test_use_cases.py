"""Use cases are tested through their ports with fakes: no database, no HTTP.

The in-memory repository is the real adapter shipped with the template, not a
test-only mock - that is the point of having it.
"""

import pytest

from cleanarch.tournaments.application import (
    AdvanceTournament,
    CreateTournament,
    CreateTournamentCommand,
    GetTournament,
    ListTournaments,
    StartTournament,
    TournamentNotFound,
)
from cleanarch.tournaments.domain import (
    TournamentAlreadyStarted,
    TournamentCreated,
    TournamentId,
    TournamentStarted,
    TournamentStatus,
)
from cleanarch.tournaments.infrastructure.in_memory import InMemoryTournamentRepository
from tests.conftest import NOW, make_phases, make_tournament

pytestmark = pytest.mark.application


@pytest.fixture
def repository() -> InMemoryTournamentRepository:
    return InMemoryTournamentRepository()


class TestCreateTournament:
    async def test_persists_and_publishes(self, repository, events, clock):
        use_case = CreateTournament(repository, events, clock)

        created = await use_case.execute(CreateTournamentCommand("Spring Cup", make_phases()))

        assert await repository.get(created.id) == created
        assert created.created_at == NOW, "time comes from the Clock port, not datetime.now()"
        assert events.events == [TournamentCreated(created.id, "Spring Cup")]


class TestStartTournament:
    async def test_starts_and_publishes(self, repository, events):
        await repository.add(make_tournament(id="t-1"))

        started = await StartTournament(repository, events).execute(TournamentId("t-1"))

        assert started.status is TournamentStatus.IN_PROGRESS
        assert (await repository.get(TournamentId("t-1"))).status is TournamentStatus.IN_PROGRESS
        assert events.events == [TournamentStarted("t-1")]

    async def test_unknown_id_raises_not_found(self, repository, events):
        with pytest.raises(TournamentNotFound):
            await StartTournament(repository, events).execute(TournamentId("missing"))

    async def test_domain_error_leaves_state_and_events_untouched(self, repository, events):
        await repository.add(make_tournament(id="t-1").start().aggregate)

        with pytest.raises(TournamentAlreadyStarted):
            await StartTournament(repository, events).execute(TournamentId("t-1"))

        assert events.events == []


class TestAdvanceTournament:
    async def test_advances_until_finished(self, repository, events):
        await repository.add(make_tournament(id="t-1", rounds=1, with_bracket=False))
        await StartTournament(repository, events).execute(TournamentId("t-1"))

        finished = await AdvanceTournament(repository, events).execute(TournamentId("t-1"))

        assert finished.status is TournamentStatus.FINISHED
        assert [type(e).__name__ for e in events.events] == [
            "TournamentStarted",
            "TournamentFinished",
        ]


class TestQueries:
    async def test_get_returns_tournament(self, repository):
        tournament = make_tournament(id="t-1")
        await repository.add(tournament)

        assert await GetTournament(repository).execute(TournamentId("t-1")) == tournament

    async def test_get_unknown_raises(self, repository):
        with pytest.raises(TournamentNotFound):
            await GetTournament(repository).execute(TournamentId("nope"))

    async def test_list_paginates_in_creation_order(self, repository):
        for i in range(5):
            created_at = NOW.replace(minute=i)
            await repository.add(make_tournament(id=f"t-{i}", created_at=created_at))

        page = await ListTournaments(repository).execute(limit=2, offset=2)

        assert [t.id for t in page] == ["t-2", "t-3"]
