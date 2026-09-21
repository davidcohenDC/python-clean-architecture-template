"""One contract, every adapter.

The in-memory and the SQLAlchemy repositories are declared interchangeable. This file
is what makes that claim true: the same tests run against both, including the
optimistic-concurrency guarantee that a stale write never silently overwrites a
newer one. Set ``TEST_DATABASE_URL`` to run the SQL half against PostgreSQL.
"""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

import pytest

from cleanarch.shared.application.errors import ConflictError
from cleanarch.shared.infrastructure.database import Base, make_engine, make_session_factory
from cleanarch.tournaments.application.ports import TournamentRepository
from cleanarch.tournaments.domain import TournamentId, TournamentStatus
from cleanarch.tournaments.infrastructure.in_memory import InMemoryTournamentRepository
from cleanarch.tournaments.infrastructure.sqlalchemy import SqlAlchemyTournamentRepository
from tests.conftest import NOW
from tests.tournaments.conftest import make_tournament

pytestmark = [pytest.mark.integration, pytest.mark.proof("repository-contract")]

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite://")


@dataclass
class Backend:
    """A repository factory plus a way to commit, for adapters that have transactions.

    ``open()`` returns an *independent* repository: for SQL, a new session on the same
    database, which is how two concurrent requests see each other.
    """

    name: str
    open: Callable[[], Awaitable[tuple[TournamentRepository, Callable[[], Awaitable[None]]]]]


async def _noop() -> None:
    return None


@pytest.fixture(params=["in_memory", "sqlalchemy"])
async def backend(request: pytest.FixtureRequest) -> AsyncIterator[Backend]:
    if request.param == "in_memory":
        shared = InMemoryTournamentRepository()

        async def open_memory() -> tuple[TournamentRepository, Callable[[], Awaitable[None]]]:
            return shared, _noop

        yield Backend("in_memory", open_memory)
        return

    engine = make_engine(DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    sessions = []

    async def open_sql() -> tuple[TournamentRepository, Callable[[], Awaitable[None]]]:
        session = factory()
        sessions.append(session)
        return SqlAlchemyTournamentRepository(session), session.commit

    yield Backend("sqlalchemy", open_sql)
    for session in sessions:
        await session.close()
    await engine.dispose()


async def test_add_then_get_round_trips_and_starts_at_version_zero(backend: Backend):
    repo, commit = await backend.open()
    tournament = make_tournament(id="t-1")

    await repo.add(tournament)
    await commit()
    other, _ = await backend.open()
    loaded = await other.get(TournamentId("t-1"))

    assert loaded == tournament
    assert loaded is not None and loaded.version == 0


async def test_get_unknown_returns_none(backend: Backend):
    repo, _ = await backend.open()
    assert await repo.get(TournamentId("missing")) is None


async def test_save_returns_the_stored_state_with_a_bumped_version(backend: Backend):
    repo, commit = await backend.open()
    await repo.add(make_tournament(id="t-1"))
    await commit()

    loaded = await repo.get(TournamentId("t-1"))
    assert loaded is not None
    saved = await repo.save(loaded.start().aggregate)
    await commit()

    assert saved.status is TournamentStatus.IN_PROGRESS
    assert saved.version == 1
    reloaded, _ = await backend.open()
    assert await reloaded.get(TournamentId("t-1")) == saved


@pytest.mark.proof("optimistic-concurrency")
async def test_a_stale_write_never_overwrites_a_newer_one(backend: Backend):
    """Two independent readers load the same state; the second writer must fail."""
    setup, commit = await backend.open()
    await setup.add(make_tournament(id="t-1", rounds=2))
    await commit()

    first, commit_first = await backend.open()
    second, _ = await backend.open()
    seen_by_first = await first.get(TournamentId("t-1"))
    seen_by_second = await second.get(TournamentId("t-1"))
    assert seen_by_first is not None and seen_by_second is not None

    await first.save(seen_by_first.start().aggregate)
    await commit_first()

    with pytest.raises(ConflictError):
        await second.save(seen_by_second.start().aggregate)

    reader, _ = await backend.open()
    final = await reader.get(TournamentId("t-1"))
    assert final is not None
    assert final.version == 1, "exactly one write went through"
    assert final.status is TournamentStatus.IN_PROGRESS


@pytest.mark.proof("optimistic-concurrency")
async def test_saving_from_a_version_that_was_already_superseded_is_a_conflict(backend):
    repo, commit = await backend.open()
    await repo.add(make_tournament(id="t-1"))
    await commit()
    loaded = await repo.get(TournamentId("t-1"))
    assert loaded is not None

    await repo.save(loaded.start().aggregate)  # version 0 -> 1
    await commit()

    with pytest.raises(ConflictError):
        await repo.save(loaded.start().aggregate)  # still claims version 0


async def test_list_is_ordered_by_creation_and_paginates(backend: Backend):
    repo, commit = await backend.open()
    for i in range(5):
        await repo.add(make_tournament(id=f"t-{i}", created_at=NOW.replace(minute=i)))
    await commit()

    page = await repo.list(limit=2, offset=1)

    assert [t.id for t in page] == ["t-1", "t-2"]
