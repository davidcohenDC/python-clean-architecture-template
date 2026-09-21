"""Fixtures and helpers every test may use. Nothing here depends on a feature.

Organise your tests however you like - by ring, by feature, next to the code - the
template only assumes ``pytest`` and these few helpers.
"""

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import Settings, create_app
from cleanarch.shared.application.actor import Actor
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.infrastructure.clock import FixedClock

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
ALICE = Actor("alice")
BOB = Actor("bob")
ADMIN = Actor("root", frozenset({"admin"}))
API_KEYS = {"alice-key": "alice", "bob-key": "bob", "root-key": "root:admin"}


def make_settings(**overrides: object) -> Settings:
    """Settings for tests: explicit values only, never the developer's ``.env``."""
    return Settings(_env_file=None, environment="test", **overrides)  # type: ignore[arg-type]


class RecordingEventPublisher:
    """``EventPublisher`` that remembers what was published."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        self.events.extend(events)


@pytest.fixture
def events() -> RecordingEventPublisher:
    return RecordingEventPublisher()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


async def make_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """The real app, in-process, with the adapters ``settings`` selects."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Open API with in-memory adapters (no database): everyone is the anonymous actor."""
    async for c in make_client(make_settings(database_url="memory://")):
        yield c


@pytest.fixture
async def secured_client() -> AsyncIterator[AsyncClient]:
    """Same app with API keys configured (see ``API_KEYS``)."""
    async for c in make_client(make_settings(database_url="memory://", api_keys=API_KEYS)):
        yield c
