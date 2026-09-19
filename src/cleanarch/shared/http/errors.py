"""Translate inside-world exceptions into HTTP responses.

Mapping rules (from most to least specific):

* ``NotFoundError``        → 404
* ``ApplicationError``     → 409  (the request is well-formed but cannot be fulfilled)
* ``DomainError``          → 422  (the request violates a business rule)
* anything else            → 500, logged

Features may register their own, more specific mapping with
``register_error(app, ExcType, status)`` if 422/409 is not right for them.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from cleanarch.shared.application.errors import ApplicationError, NotFoundError
from cleanarch.shared.domain.errors import DomainError
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
    register_error(app, ApplicationError, status.HTTP_409_CONFLICT)
    register_error(app, DomainError, status.HTTP_422_UNPROCESSABLE_CONTENT)

    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        body = ErrorResponse(error="InternalServerError", message="Unexpected error.")
        return JSONResponse(status_code=500, content=body.model_dump())

    app.add_exception_handler(Exception, unexpected)
