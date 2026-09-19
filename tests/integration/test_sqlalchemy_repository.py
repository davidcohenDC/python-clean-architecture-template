"""The SQLAlchemy adapter against a real (SQLite in-memory) database.

Set ``TEST_DATABASE_URL`` to run the same tests against PostgreSQL:

    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_test
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch.shared.infrastructure.database import Base, make_engine, make_session_factory
from cleanarch.tournaments.domain import TournamentId, TournamentStatus
from cleanarch.tournaments.infrastructure.sqlalchemy import SqlAlchemyTournamentRepository
from tests.conftest import make_tournament

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = make_engine(DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with make_session_factory(engine)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def repository(session: AsyncSession) -> SqlAlchemyTournamentRepository:
    return SqlAlchemyTournamentRepository(session)


async def test_add_then_get_round_trips_the_whole_aggregate(repository, session):
    tournament = make_tournament(id="t-1")

    await repository.add(tournament)
    await session.commit()
    session.expunge_all()  # force a real re-read from the database

    assert await repository.get(TournamentId("t-1")) == tournament


async def test_get_unknown_returns_none(repository):
    assert await repository.get(TournamentId("missing")) is None


async def test_save_updates_existing_row(repository, session):
    tournament = make_tournament(id="t-1")
    await repository.add(tournament)
    await session.commit()

    await repository.save(tournament.start().aggregate)
    await session.commit()
    session.expunge_all()

    reloaded = await repository.get(TournamentId("t-1"))
    assert reloaded is not None
    assert reloaded.status is TournamentStatus.IN_PROGRESS
    assert reloaded.progress.phase_index == 0


async def test_list_orders_and_paginates(repository, session):
    for i in range(5):
        await repository.add(make_tournament(id=f"t-{i}"))
    await session.commit()

    page = await repository.list(limit=2, offset=1)

    assert [t.id for t in page] == ["t-1", "t-2"]
