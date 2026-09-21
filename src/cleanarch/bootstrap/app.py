"""Build the FastAPI app and wire every port to an adapter.

Read this file top to bottom and you know how the whole system is assembled:

1. settings decide which adapters to use;
2. middlewares give each request a transaction, then dispatch its events
   after the commit (``bootstrap/transaction.py``);
3. shared ports (clock, events, actor) get their providers;
4. every feature listed in ``bootstrap/features`` wires itself: adapters,
   router, subscribers.

Adding a feature = one module in ``bootstrap/features/`` and one entry in its
``FEATURES`` list (``scripts/new_feature.py`` does both).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.engine import make_url

from cleanarch import __version__
from cleanarch.bootstrap.events import build_event_bus
from cleanarch.bootstrap.features import FEATURES
from cleanarch.bootstrap.logging import configure_logging
from cleanarch.bootstrap.settings import Settings, get_settings
from cleanarch.bootstrap.transaction import (
    EventDispatchMiddleware,
    TransactionMiddleware,
    get_events,
)
from cleanarch.shared.http.dependencies import get_clock, get_event_publisher
from cleanarch.shared.http.errors import register_error_handlers
from cleanarch.shared.http.request_id import RequestIdMiddleware
from cleanarch.shared.infrastructure.clock import SystemClock
from cleanarch.shared.infrastructure.database import make_engine, make_session_factory

logger = logging.getLogger(__name__)


def wire_shared(app: FastAPI, settings: Settings) -> None:
    app.state.actors = settings.actors  # read by shared.http.auth.get_actor
    app.dependency_overrides[get_event_publisher] = get_events  # per-request collector
    clock = SystemClock()
    app.dependency_overrides[get_clock] = lambda: clock


def _redacted(database_url: str) -> str:
    """The URL for logs: never the password."""
    if database_url.startswith("memory://"):
        return database_url
    return make_url(database_url).render_as_string(hide_password=True)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("%s started (database=%s)", settings.app_name, _redacted(settings.database_url))
        yield
        if not settings.use_in_memory:
            await app.state.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        description="Clean Architecture reference API.",
    )
    register_error_handlers(app)

    # Middlewares, innermost first (Starlette wraps each new one around the previous):
    # transaction -> event dispatch -> request id. See bootstrap/transaction.py.
    if not settings.use_in_memory:
        # Creating the engine opens no connection; the first request does.
        app.state.engine = make_engine(settings.database_url, echo=settings.database_echo)
        app.state.session_factory = make_session_factory(app.state.engine)
        app.add_middleware(TransactionMiddleware, session_factory=app.state.session_factory)
    app.state.event_bus = build_event_bus()
    app.add_middleware(
        EventDispatchMiddleware, bus=app.state.event_bus, transactional=not settings.use_in_memory
    )
    app.add_middleware(RequestIdMiddleware)

    wire_shared(app, settings)
    for feature in FEATURES:
        if wire_http := getattr(feature, "wire_http", None):
            wire_http(app, settings)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/ready", tags=["ops"], summary="Readiness probe (checks the database)")
    async def ready(request: Request, response: Response) -> dict[str, str]:
        if settings.use_in_memory:
            return {"status": "ready", "database": "memory"}
        try:
            async with request.app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            logger.exception("readiness check failed")
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not ready", "database": "unreachable"}
        return {"status": "ready", "database": "ok"}

    return app
