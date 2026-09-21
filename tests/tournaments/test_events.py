"""Transaction/event semantics, observed from the outside (ADR-005).

    request -> use case -> repository (flush) -> commit -> handlers

These tests use a SQLite *file* so that a handler opening its own session really
cannot see uncommitted rows - the in-memory database shares one connection and
would hide the difference.
"""

import logging
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch.bootstrap import create_app
from cleanarch.shared.infrastructure.database import Base
from cleanarch.tournaments.domain import TournamentCreated, TournamentStarted
from cleanarch.tournaments.infrastructure.sqlalchemy import TournamentModel
from tests.conftest import make_settings
from tests.tournaments.conftest import VALID_PAYLOAD

pytestmark = [pytest.mark.api, pytest.mark.proof("events-after-commit")]

BASE = "/api/v1/tournaments"


@pytest.fixture
async def file_app(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, object, list[str]]]:
    app = create_app(make_settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'events.db'}"))
    log: list[str] = []

    async def count_rows_from_a_fresh_session(event: TournamentCreated) -> None:
        async with app.state.session_factory() as session:
            rows = await session.scalar(select(func.count()).select_from(TournamentModel))
        log.append(f"handler saw {rows} committed row(s)")

    app.state.event_bus.subscribe(TournamentCreated, count_rows_from_a_fresh_session)

    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app, log


async def test_handlers_run_after_commit_and_see_the_committed_state(file_app):
    client, _, log = file_app

    response = await client.post(BASE, json=VALID_PAYLOAD)

    assert response.status_code == 201
    assert log == ["handler saw 1 committed row(s)"]


async def test_a_rolled_back_request_dispatches_nothing(file_app):
    client, app, _ = file_app
    started: list[str] = []

    async def on_started(event: TournamentStarted) -> None:
        started.append(event.tournament_id)

    app.state.event_bus.subscribe(TournamentStarted, on_started)
    created = (await client.post(BASE, json=VALID_PAYLOAD)).json()
    await client.post(f"{BASE}/{created['id']}/start")
    assert started == [created["id"]]

    second_start = await client.post(f"{BASE}/{created['id']}/start")  # domain error -> 422

    assert second_start.status_code == 422
    assert started == [created["id"]], "the failed request published nothing"


async def test_a_failed_commit_dispatches_nothing(file_app, monkeypatch):
    client, _, log = file_app

    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("database gone")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)
    response = await client.post(BASE, json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert log == []


async def test_a_failing_handler_is_logged_and_does_not_change_the_response(file_app, caplog):
    client, app, log = file_app

    async def broken(event: TournamentCreated) -> None:
        raise RuntimeError("mail server down")

    async def still_runs(event: TournamentCreated) -> None:
        log.append("second handler ran")

    app.state.event_bus.subscribe(TournamentCreated, broken)
    app.state.event_bus.subscribe(TournamentCreated, still_runs)

    with caplog.at_level(logging.ERROR):
        response = await client.post(BASE, json=VALID_PAYLOAD)

    assert response.status_code == 201, "the state is committed; the response must say so"
    assert "event handler" in caplog.text and "mail server down" in caplog.text
    assert log == ["handler saw 1 committed row(s)", "second handler ran"]


async def test_in_memory_mode_dispatches_on_success_without_a_transaction():
    app = create_app(make_settings(database_url="memory://"))
    seen: list[str] = []

    async def on_created(event: TournamentCreated) -> None:
        seen.append(event.name)

    app.state.event_bus.subscribe(TournamentCreated, on_created)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://t") as client,
    ):
        await client.post(BASE, json=VALID_PAYLOAD)
        await client.post(BASE, json={**VALID_PAYLOAD, "name": "  "})  # 422, dropped

    assert seen == ["Spring Cup"]
