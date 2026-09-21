"""HTTP -> use case -> SQLAlchemy -> database, end to end on SQLite.

The other API tests use in-memory adapters. These two cover the one path a user
actually runs, and the guarantee ADR-004 makes: nothing is persisted unless the
commit succeeded *before* the response was sent.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch.bootstrap import create_app
from cleanarch.shared.infrastructure.database import Base
from cleanarch.tournaments.infrastructure.sqlalchemy import TournamentModel
from tests.api.conftest import VALID_PAYLOAD
from tests.conftest import make_settings

pytestmark = pytest.mark.api

BASE = "/api/v1/tournaments"


@pytest.fixture
async def sqlite_app() -> AsyncIterator[tuple[AsyncClient, object]]:
    app = create_app(make_settings(database_url="sqlite+aiosqlite://"))
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def count_rows(app) -> int:  # type: ignore[no-untyped-def]
    async with app.state.session_factory() as session:
        return (await session.scalar(select(func.count()).select_from(TournamentModel))) or 0


async def test_create_persists_and_reloads_through_the_database(sqlite_app):
    client, app = sqlite_app

    created = await client.post(BASE, json=VALID_PAYLOAD)
    assert created.status_code == 201, created.text
    started = await client.post(f"{BASE}/{created.json()['id']}/start")
    reloaded = await client.get(f"{BASE}/{created.json()['id']}")

    assert started.status_code == 200
    assert reloaded.json()["progress"]["status"] == "in_progress"
    assert await count_rows(app) == 1


async def test_domain_error_rolls_back_the_request(sqlite_app):
    client, app = sqlite_app
    created = await client.post(BASE, json=VALID_PAYLOAD)
    await client.post(f"{BASE}/{created.json()['id']}/start")

    response = await client.post(f"{BASE}/{created.json()['id']}/start")

    assert response.status_code == 422
    assert await count_rows(app) == 1


async def test_failed_commit_is_a_500_and_nothing_is_persisted(sqlite_app, monkeypatch):
    client, app = sqlite_app

    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("database gone")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    response = await client.post(BASE, json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert response.json() == {"error": "TransactionFailed", "message": "Changes were not saved."}
    monkeypatch.undo()
    assert await count_rows(app) == 0
