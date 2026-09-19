"""HTTP boundary tests run the real app with in-memory adapters.

``DATABASE_URL=memory://`` makes ``create_app`` wire the in-memory repository,
so these tests cover routing, validation, serialisation and error mapping
without touching a database. ``tests/integration`` covers the SQL adapter.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import Settings, create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(Settings(database_url="memory://", environment="test"))
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


VALID_PAYLOAD = {
    "name": "Spring Cup",
    "phases": [
        {"config": {"kind": "round", "rounds": 2, "pairing": "swiss"}},
        {"config": {"kind": "bracket", "elimination": "single"}, "cut": {"players": 8}},
    ],
}
