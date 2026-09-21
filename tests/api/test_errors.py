"""The HTTP error contract, status by status (see shared/http/errors.py)."""

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import create_app
from tests.api.conftest import VALID_PAYLOAD
from tests.conftest import make_settings

pytestmark = pytest.mark.api

BASE = "/api/v1/tournaments"


async def test_unknown_route_is_404_in_the_envelope(client: AsyncClient):
    response = await client.get("/no/such/route")
    assert response.status_code == 404
    assert response.json() == {"error": "NotFound", "message": "Not Found"}


async def test_unknown_resource_is_404_with_a_specific_error(client: AsyncClient):
    response = await client.get(f"{BASE}/missing")
    assert response.status_code == 404
    assert response.json()["error"] == "TournamentNotFound"


async def test_wrong_method_is_405_and_keeps_the_allow_header(client: AsyncClient):
    response = await client.delete(BASE)
    assert response.status_code == 405
    assert response.json()["error"] == "MethodNotAllowed"
    assert "POST" in response.headers["allow"]


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


async def test_unexpected_exception_is_500_with_request_id_in_response_and_log(caplog):
    app = create_app(make_settings(database_url="memory://"))

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("kaboom")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    caplog.set_level(logging.ERROR)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://t") as client,
    ):
        response = await client.get("/boom", headers={"X-Request-ID": "trace-500"})

    assert response.status_code == 500
    assert response.json() == {"error": "InternalServerError", "message": "Unexpected error."}
    assert response.headers["x-request-id"] == "trace-500"
    record = next(r for r in caplog.records if r.getMessage() == "unhandled error")
    assert record.request_id == "trace-500"  # type: ignore[attr-defined]
    assert "kaboom" in caplog.text
