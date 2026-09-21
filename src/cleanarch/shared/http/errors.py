"""Translate inside-world exceptions into HTTP responses.

Mapping rules (from most to least specific):

* ``NotFoundError``        → 404
* ``ForbiddenError``       → 403
* ``ConflictError``        → 409  (stale write, optimistic concurrency)
* ``ApplicationError``     → 409  (the request is well-formed but cannot be fulfilled)
* ``DomainError``          → 422  (the request violates a business rule)
* ``HTTPException``        → its own status, same envelope: 401 from auth, 404 for an
                             unknown route, 405 with its ``Allow`` header
* anything else            → 500, logged with the request id, which is also echoed in
                             the response header

One deliberate exception: Pydantic's request validation keeps FastAPI's native
``{"detail": [...]}`` body. Clients and tooling already understand that format,
and it carries field locations the envelope does not.

Features may register their own, more specific mapping with
``register_error(app, ExcType, status)`` if 422/409 is not right for them.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from cleanarch.shared.application.errors import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.http.request_id import REQUEST_ID_HEADER
from cleanarch.shared.http.schemas import ErrorResponse

logger = logging.getLogger(__name__)


def _response(exc: Exception, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=type(exc).__name__, message=str(exc))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_error(app: FastAPI, exc_type: type[Exception], status_code: int) -> None:
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return _response(exc, status_code)

    app.add_exception_handler(exc_type, handler)


def register_error_handlers(app: FastAPI) -> None:
    register_error(app, NotFoundError, status.HTTP_404_NOT_FOUND)
    register_error(app, ForbiddenError, status.HTTP_403_FORBIDDEN)
    register_error(app, ConflictError, status.HTTP_409_CONFLICT)
    register_error(app, ApplicationError, status.HTTP_409_CONFLICT)
    register_error(app, DomainError, status.HTTP_422_UNPROCESSABLE_CONTENT)

    async def http_exception(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, HTTPException)
        names = {401: "Unauthorized", 403: "Forbidden", 404: "NotFound", 405: "MethodNotAllowed"}
        body = ErrorResponse(error=names.get(exc.status_code, "HTTPError"), message=str(exc.detail))
        return JSONResponse(
            status_code=exc.status_code, content=body.model_dump(), headers=exc.headers
        )

    app.add_exception_handler(HTTPException, http_exception)

    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Runs in Starlette's outermost ServerErrorMiddleware, outside RequestIdMiddleware:
        # the id is taken from the scope state it left behind and echoed by hand.
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled error", exc_info=exc, extra={"request_id": request_id or "-"})
        body = ErrorResponse(error="InternalServerError", message="Unexpected error.")
        headers = {REQUEST_ID_HEADER: request_id} if request_id else None
        return JSONResponse(status_code=500, content=body.model_dump(), headers=headers)

    app.add_exception_handler(Exception, unexpected)
