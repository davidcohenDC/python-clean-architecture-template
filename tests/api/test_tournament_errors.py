"""Error rows that need the example feature: resource 404, shape vs rule 422."""

import pytest
from httpx import AsyncClient

from tests.api.conftest import VALID_PAYLOAD

pytestmark = pytest.mark.api

BASE = "/api/v1/tournaments"


async def test_unknown_resource_is_404_with_a_specific_error(client: AsyncClient):
    response = await client.get(f"{BASE}/missing")
    assert response.status_code == 404
    assert response.json()["error"] == "TournamentNotFound"


async def test_pydantic_validation_keeps_fastapi_native_422(client: AsyncClient):
    """Deliberate: field locations matter more than envelope uniformity here."""
    response = await client.post(BASE, json={"name": 1})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and "error" not in body
    assert body["detail"][0]["loc"][0] == "body"


async def test_domain_rule_violation_is_422_in_the_envelope(client: AsyncClient):
    response = await client.post(BASE, json={**VALID_PAYLOAD, "name": "   "})
    assert response.status_code == 422
    assert response.json() == {
        "error": "InvalidTournamentName",
        "message": "Tournament name must be 1-100 non-blank characters.",
    }
