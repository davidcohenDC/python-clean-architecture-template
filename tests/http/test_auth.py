"""API-key authentication on a route of its own: what every feature inherits."""

from collections.abc import AsyncIterator
from typing import Annotated

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import Settings, create_app
from cleanarch.shared.application.actor import Actor
from cleanarch.shared.http.auth import get_actor
from tests.conftest import API_KEYS, make_settings


async def whoami_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)

    @app.get("/whoami")
    async def whoami(actor: Annotated[Actor, Depends(get_actor)]) -> dict[str, object]:
        return {"id": actor.id, "roles": sorted(actor.roles), "admin": actor.is_admin}

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def open_api() -> AsyncIterator[AsyncClient]:
    async for c in whoami_client(make_settings(database_url="memory://")):
        yield c


@pytest.fixture
async def secured_api() -> AsyncIterator[AsyncClient]:
    async for c in whoami_client(make_settings(database_url="memory://", api_keys=API_KEYS)):
        yield c


async def test_without_keys_everyone_is_anonymous(open_api: AsyncClient):
    response = await open_api.get("/whoami", headers={"X-API-Key": "anything"})
    assert response.status_code == 200
    assert response.json() == {"id": "anonymous", "roles": [], "admin": False}


async def test_with_keys_a_missing_or_unknown_key_is_401(secured_api: AsyncClient):
    missing = await secured_api.get("/whoami")
    unknown = await secured_api.get("/whoami", headers={"X-API-Key": "nope"})
    for response in (missing, unknown):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "ApiKey"
        assert response.json()["error"] == "Unauthorized"


async def test_a_key_resolves_to_its_actor_and_roles(secured_api: AsyncClient):
    alice = await secured_api.get("/whoami", headers={"X-API-Key": "alice-key"})
    root = await secured_api.get("/whoami", headers={"X-API-Key": "root-key"})
    assert alice.json() == {"id": "alice", "roles": [], "admin": False}
    assert root.json() == {"id": "root", "roles": ["admin"], "admin": True}


async def test_the_scheme_is_part_of_the_openapi_document(secured_api: AsyncClient):
    schema = (await secured_api.get("/openapi.json")).json()
    scheme = schema["components"]["securitySchemes"]["APIKeyHeader"]
    assert scheme == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "Required only when API_KEYS is configured.",
    }
