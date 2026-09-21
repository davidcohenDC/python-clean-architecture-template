"""Operational endpoints and request correlation."""

import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from cleanarch.bootstrap import create_app
from cleanarch.bootstrap.logging import JsonFormatter, RequestIdFilter
from cleanarch.shared.http.request_id import request_id_var
from tests.api.conftest import make_client
from tests.conftest import make_settings

pytestmark = pytest.mark.api


@pytest.mark.proof("error-contract")
async def test_every_response_carries_a_request_id(client: AsyncClient):
    generated = await client.get("/health")
    echoed = await client.get("/health", headers={"X-Request-ID": "trace-123"})
    rejected = await client.get("/health", headers={"X-Request-ID": "bad id with spaces"})

    assert len(generated.headers["x-request-id"]) == 32
    assert echoed.headers["x-request-id"] == "trace-123"
    assert rejected.headers["x-request-id"] != "bad id with spaces"


async def test_ready_reports_memory_backend(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "memory"}


async def test_ready_checks_the_database():
    async for client in make_client(make_settings(database_url="sqlite+aiosqlite://")):
        response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json()["database"] == "ok"


async def test_ready_is_503_when_the_database_is_unreachable():
    settings = make_settings(database_url="postgresql+asyncpg://nobody@127.0.0.1:1/none")
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://t") as client,
    ):
        response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not ready"


def test_json_log_lines_include_the_request_id():
    record = logging.LogRecord("app", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    token = request_id_var.set("req-42")
    try:
        assert RequestIdFilter().filter(record)
    finally:
        request_id_var.reset(token)

    line = json.loads(JsonFormatter().format(record))

    assert line["message"] == "hello world"
    assert line["request_id"] == "req-42"
    assert line["level"] == "INFO"
