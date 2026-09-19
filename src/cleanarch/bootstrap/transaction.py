"""Transaction per request, done at the point where it is actually safe.

Why a middleware and not a ``yield`` dependency? Since FastAPI 0.118 the exit
code of a ``yield`` dependency runs *after* the response has been sent, so a
``commit()`` there can fail while the client already holds a ``201``. This
middleware commits *before* the response leaves the process and turns a failed
commit into a ``500``.

Rules:

* one ``AsyncSession`` per request, exposed as ``request.state.session``;
* status ``< 400``  -> commit;  ``>= 400`` or exception -> rollback;
* commit failure    -> rollback, log, ``500`` with the usual error envelope.

It lives in ``bootstrap`` because it is glue between two adapters (HTTP and the
database), and adapters never import each other.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cleanarch.shared.http.schemas import ErrorResponse

logger = logging.getLogger(__name__)


class TransactionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        async with self._session_factory() as session:
            request.state.session = session
            try:
                response = await call_next(request)
            except BaseException:
                await session.rollback()
                raise
            if response.status_code >= 400:
                await session.rollback()
                return response
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("commit failed")
                body = ErrorResponse(error="TransactionFailed", message="Changes were not saved.")
                return JSONResponse(status_code=500, content=body.model_dump())
            return response


def get_session(request: Request) -> AsyncSession:
    """FastAPI dependency: the session opened by ``TransactionMiddleware``."""
    session: AsyncSession = request.state.session
    return session
