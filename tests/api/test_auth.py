"""API-key authentication (HTTP adapter) and organizer authorization (application)."""

import pytest
from httpx import AsyncClient

from tests.api.conftest import VALID_PAYLOAD

pytestmark = pytest.mark.api

BASE = "/api/v1/tournaments"
ALICE = {"X-API-Key": "alice-key"}
BOB = {"X-API-Key": "bob-key"}
ROOT = {"X-API-Key": "root-key"}


async def test_open_api_without_keys_runs_as_anonymous(client: AsyncClient):
    response = await client.post(BASE, json=VALID_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["organizer_id"] == "anonymous"


async def test_missing_key_is_401_with_envelope(secured_client: AsyncClient):
    response = await secured_client.post(BASE, json=VALID_PAYLOAD)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"
    assert response.json() == {"error": "Unauthorized", "message": "Missing or invalid API key."}


async def test_wrong_key_is_401(secured_client: AsyncClient):
    response = await secured_client.post(BASE, json=VALID_PAYLOAD, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


async def test_reads_stay_public(secured_client: AsyncClient):
    assert (await secured_client.get(BASE)).status_code == 200


async def test_caller_becomes_organizer_and_only_they_can_start(secured_client: AsyncClient):
    created = await secured_client.post(BASE, json=VALID_PAYLOAD, headers=ALICE)
    assert created.json()["organizer_id"] == "alice"
    url = f"{BASE}/{created.json()['id']}/start"

    as_bob = await secured_client.post(url, headers=BOB)
    as_alice = await secured_client.post(url, headers=ALICE)

    assert as_bob.status_code == 403
    assert as_bob.json()["error"] == "ForbiddenError"
    assert as_alice.status_code == 200


async def test_admin_can_manage_any_tournament(secured_client: AsyncClient):
    created = await secured_client.post(BASE, json=VALID_PAYLOAD, headers=ALICE)

    response = await secured_client.post(f"{BASE}/{created.json()['id']}/start", headers=ROOT)

    assert response.status_code == 200


async def test_openapi_documents_the_api_key_scheme(secured_client: AsyncClient):
    schema = (await secured_client.get("/openapi.json")).json()
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]
