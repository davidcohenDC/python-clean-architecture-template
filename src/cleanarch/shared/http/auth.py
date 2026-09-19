"""API-key authentication: an HTTP adapter that produces an ``Actor``.

``bootstrap`` publishes the key table on ``app.state.actors``; with no keys
configured every request runs as ``ANONYMOUS`` so that ``make run`` works out
of the box. Configure ``API_KEYS`` and the same endpoints require
``X-API-Key``. Swap this file for JWT or sessions without touching a use case.

This is a real dependency (not a placeholder overridden in bootstrap) so that
the security scheme shows up in OpenAPI and Swagger's *Authorize* button works.
"""

from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from cleanarch.shared.application.actor import ANONYMOUS, Actor

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Required only when API_KEYS is configured.",
)


async def get_actor(
    request: Request, api_key: Annotated[str | None, Security(API_KEY_HEADER)]
) -> Actor:
    keys: dict[str, Actor] = getattr(request.app.state, "actors", {})
    if not keys:
        return ANONYMOUS
    actor = keys.get(api_key) if api_key else None
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return actor
