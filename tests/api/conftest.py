"""HTTP boundary tests run the real app with in-memory adapters.

``DATABASE_URL=memory://`` makes ``create_app`` wire the in-memory repository,
so these tests cover routing, validation, serialisation and error mapping
without touching a database. ``tests/integration`` covers the SQL adapter.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import Settings, create_app
from tests.conftest import make_settings

API_KEYS = {"alice-key": "alice", "bob-key": "bob", "root-key": "root:admin"}


async def make_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Open API (no API_KEYS): everyone is the anonymous actor."""
    async for c in make_client(make_settings(database_url="memory://")):
        yield c


@pytest.fixture
async def secured_client() -> AsyncIterator[AsyncClient]:
    """Same app with API keys configured."""
    settings = make_settings(database_url="memory://", api_keys=API_KEYS)
    async for c in make_client(settings):
        yield c


# >>> example: tournaments
VALID_PAYLOAD = {
    "name": "Spring Cup",
    "phases": [
        {"config": {"kind": "round", "rounds": 2, "pairing": "swiss"}},
        {"config": {"kind": "bracket", "elimination": "single"}, "cut": {"players": 8}},
    ],
}
# <<< example: tournaments
