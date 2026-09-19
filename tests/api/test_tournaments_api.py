import pytest
from httpx import AsyncClient

from tests.api.conftest import VALID_PAYLOAD

pytestmark = pytest.mark.api

BASE = "/api/v1/tournaments"


async def create(client: AsyncClient, **overrides) -> dict:
    response = await client.post(BASE, json={**VALID_PAYLOAD, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_create_returns_201_with_full_representation(client):
    body = await create(client)

    assert body["name"] == "Spring Cup"
    assert body["progress"] == {"status": "not_started", "phase_index": None, "round_index": None}
    assert body["phases"][1]["cut"] == {"players": 8}


async def test_get_and_list(client):
    created = await create(client)

    detail = await client.get(f"{BASE}/{created['id']}")
    listing = await client.get(BASE, params={"limit": 10})

    assert detail.status_code == 200 and detail.json() == created
    assert [t["id"] for t in listing.json()] == [created["id"]]


async def test_start_then_advance_walks_the_state_machine(client):
    created = await create(client)

    started = await client.post(f"{BASE}/{created['id']}/start")
    advanced = await client.post(f"{BASE}/{created['id']}/advance")

    assert started.json()["progress"] == {
        "status": "in_progress",
        "phase_index": 0,
        "round_index": 0,
    }
    assert advanced.json()["progress"] == {
        "status": "in_progress",
        "phase_index": 0,
        "round_index": 1,
    }


# -- error mapping -----------------------------------------------------------------


async def test_unknown_id_maps_to_404(client):
    response = await client.get(f"{BASE}/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": "TournamentNotFound",
        "message": "Tournament 'does-not-exist' not found.",
    }


async def test_domain_rule_violation_maps_to_422(client):
    created = await create(client)
    await client.post(f"{BASE}/{created['id']}/start")

    response = await client.post(f"{BASE}/{created['id']}/start")

    assert response.status_code == 422
    assert response.json()["error"] == "TournamentAlreadyStarted"


async def test_invalid_phases_are_a_domain_error_not_a_pydantic_error(client):
    payload = {**VALID_PAYLOAD, "phases": [{"config": {"kind": "round", "rounds": 99}}]}

    response = await client.post(BASE, json=payload)

    assert response.status_code == 422
    assert response.json()["error"] == "InvalidPhases"


async def test_malformed_payload_is_rejected_by_pydantic(client):
    response = await client.post(BASE, json={"name": "x", "phases": "nope", "extra": 1})
    assert response.status_code == 422
    assert "detail" in response.json()  # FastAPI's native validation envelope
