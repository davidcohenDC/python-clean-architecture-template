"""The unit of work around an HTTP request: transaction, then events.

Why middleware and not ``yield`` dependencies? Since FastAPI 0.118 the exit
code of a ``yield`` dependency runs *after* the response has been sent, so a
``commit()`` there can fail while the client already holds a ``201``. These
middlewares run before the response leaves the process.

Order of effects for one request (outermost first):

    RequestIdMiddleware
      EventDispatchMiddleware   collect events during the request, dispatch after commit
        TransactionMiddleware   one session; commit on success, rollback otherwise
          the endpoint

Rules:

* status ``< 400``  -> commit;  ``>= 400`` or exception -> rollback, events dropped;
* commit failure    -> rollback, ``500 TransactionFailed``, events dropped;
* after a commit    -> collected events are dispatched, in order; handler failures
                       are logged and do not change the response (ADR-005).

They live in ``bootstrap`` because they glue two adapters (HTTP and the
database); adapters never import each other.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cleanarch.shared.application.ports import EventPublisher
from cleanarch.shared.http.schemas import ErrorResponse
from cleanarch.shared.infrastructure.events import CollectedEvents, InProcessEventBus

logger = logging.getLogger(__name__)

CallNext = Callable[[Request], Awaitable[Response]]


class TransactionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
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
            request.state.committed = True
            return response


class EventDispatchMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, bus: InProcessEventBus, *, transactional: bool) -> None:
        super().__init__(app)
        self._bus = bus
        # Without a database there is no commit to wait for: dispatch on success.
        self._transactional = transactional

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        collected = CollectedEvents()
        request.state.events = collected
        request.state.committed = False
        response = await call_next(request)
        committed = request.state.committed or not self._transactional
        if committed and response.status_code < 400:
            await self._bus.dispatch(collected.drain())
        return response


def get_session(request: Request) -> AsyncSession:
    """FastAPI dependency: the session opened by ``TransactionMiddleware``."""
    session: AsyncSession = request.state.session
    return session


def get_events(request: Request) -> EventPublisher:
    """FastAPI dependency: the per-request ``EventPublisher`` (see ``EventDispatchMiddleware``)."""
    events: CollectedEvents = request.state.events
    return events
