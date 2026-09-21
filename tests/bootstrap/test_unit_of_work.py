"""The unit of work around a request, tested without any feature (ADR-004, ADR-005).

    request -> handler -> commit -> response -> event handlers

A stub session records what happened and in which order; a throwaway route
plays the role of a use case. This is what every feature inherits.
"""

import logging
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap.transaction import (
    EventDispatchMiddleware,
    TransactionMiddleware,
    get_events,
    get_session,
)
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.http.errors import register_error_handlers
from cleanarch.shared.infrastructure.events import InProcessEventBus


class SomethingHappened(DomainEvent):
    pass


class StubSession:
    """Records calls; ``fail_commit`` simulates a database that refuses to commit."""

    def __init__(self, log: list[str], *, fail_commit: bool = False) -> None:
        self.log, self.fail_commit = log, fail_commit

    async def __aenter__(self) -> "StubSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.log.append("close")

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("database gone")
        self.log.append("commit")

    async def rollback(self) -> None:
        self.log.append("rollback")


def build(log: list[str], *, fail_commit: bool = False) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    bus = InProcessEventBus()

    async def handler(event: SomethingHappened) -> None:
        log.append("handler")

    async def broken(event: SomethingHappened) -> None:
        raise RuntimeError("mail server down")

    bus.subscribe(SomethingHappened, broken)
    bus.subscribe(SomethingHappened, handler)
    app.add_middleware(
        TransactionMiddleware, session_factory=lambda: StubSession(log, fail_commit=fail_commit)
    )
    app.add_middleware(EventDispatchMiddleware, bus=bus, transactional=True)

    @app.post("/work")
    async def work(request: Request) -> dict[str, str]:
        assert isinstance(get_session(request), StubSession)
        log.append("write")
        await get_events(request).publish([SomethingHappened()])
        return {"status": "done"}

    @app.post("/refuse")
    async def refuse(request: Request) -> None:
        log.append("write")
        await get_events(request).publish([SomethingHappened()])
        raise HTTPException(status_code=409, detail="no")

    return app


@pytest.fixture
def log() -> list[str]:
    return []


async def call(app: FastAPI, path: str) -> AsyncIterator[tuple[int, dict[str, object]]]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        response = await client.post(path)
        yield response.status_code, response.json()


async def test_commit_happens_before_the_response_and_handlers_after_it(log, caplog):
    caplog.set_level(logging.ERROR)
    async for status, body in call(build(log), "/work"):
        assert status == 200 and body == {"status": "done"}

    assert log == ["write", "commit", "close", "handler"], "commit first, then dispatch"
    assert "mail server down" in caplog.text, "a failing handler is logged, not raised"


async def test_an_error_response_rolls_back_and_dispatches_nothing(log):
    async for status, _ in call(build(log), "/refuse"):
        assert status == 409

    assert log == ["write", "rollback", "close"]


async def test_a_failed_commit_is_a_500_and_dispatches_nothing(log):
    async for status, body in call(build(log, fail_commit=True), "/work"):
        assert status == 500
        assert body["error"] == "TransactionFailed"

    assert log == ["write", "rollback", "close"]
