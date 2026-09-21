"""Build the FastAPI app and wire every port to an adapter.

Read this file top to bottom and you know how the whole system is assembled:

1. settings decide which adapters to use;
2. shared adapters are created once; ``TransactionMiddleware`` opens one DB
   session per request and commits it before the response is sent, then
   ``EventDispatchMiddleware`` runs the handlers for the events it collected;
3. each feature's placeholder dependencies are overridden with real providers;
4. routers are mounted.

Adding a feature = one ``wire_<feature>()`` function + one call in ``create_app``.
The blocks between ``>>> example`` / ``<<< example`` markers belong to the demo
feature and are removed by ``scripts/init_project.py --remove-example``.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch import __version__
from cleanarch.bootstrap.events import build_event_bus
from cleanarch.bootstrap.logging import configure_logging
from cleanarch.bootstrap.settings import Settings, get_settings
from cleanarch.bootstrap.transaction import (
    EventDispatchMiddleware,
    TransactionMiddleware,
    get_events,
    get_session,
)
from cleanarch.shared.http.dependencies import get_clock, get_event_publisher
from cleanarch.shared.http.errors import register_error_handlers
from cleanarch.shared.http.request_id import RequestIdMiddleware
from cleanarch.shared.infrastructure.clock import SystemClock
from cleanarch.shared.infrastructure.database import make_engine, make_session_factory

# isort: split
# >>> example: tournaments
from cleanarch.tournaments.application import TournamentRepository
from cleanarch.tournaments.http import get_tournament_repository
from cleanarch.tournaments.http import router as tournaments_router
from cleanarch.tournaments.infrastructure.in_memory import InMemoryTournamentRepository
from cleanarch.tournaments.infrastructure.sqlalchemy import SqlAlchemyTournamentRepository

# <<< example: tournaments

logger = logging.getLogger(__name__)


# The session opened by TransactionMiddleware for the current request.
Session = Annotated[AsyncSession, Depends(get_session)]


# -- shared wiring -----------------------------------------------------------------


def wire_shared(app: FastAPI, settings: Settings) -> None:
    app.state.actors = settings.actors  # read by shared.http.auth.get_actor
    app.dependency_overrides[get_event_publisher] = get_events  # per-request collector
    clock = SystemClock()
    app.dependency_overrides[get_clock] = lambda: clock


# >>> example: tournaments
def wire_tournaments(app: FastAPI, settings: Settings) -> None:
    """Everything the tournaments feature needs from the outside world."""

    if settings.use_in_memory:
        repository = InMemoryTournamentRepository()
        app.dependency_overrides[get_tournament_repository] = lambda: repository
    else:

        def sqlalchemy_repository(session: Session) -> TournamentRepository:
            return SqlAlchemyTournamentRepository(session)

        app.dependency_overrides[get_tournament_repository] = sqlalchemy_repository

    app.include_router(tournaments_router, prefix="/api/v1")


# <<< example: tournaments


# -- application factory -----------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("%s started (database=%s)", settings.app_name, settings.database_url)
        yield
        if not settings.use_in_memory:
            await app.state.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        description="Clean Architecture reference API. Replace the example feature with yours.",
    )
    register_error_handlers(app)

    # Middlewares, innermost first (Starlette wraps each new one around the previous):
    # transaction -> event dispatch -> request id. See bootstrap/transaction.py.
    if not settings.use_in_memory:
        # Creating the engine opens no connection; the first request does.
        app.state.engine = make_engine(settings.database_url, echo=settings.database_echo)
        app.state.session_factory = make_session_factory(app.state.engine)
        app.add_middleware(TransactionMiddleware, session_factory=app.state.session_factory)
    app.state.event_bus = build_event_bus()  # subscribers live in bootstrap/events.py
    app.add_middleware(
        EventDispatchMiddleware, bus=app.state.event_bus, transactional=not settings.use_in_memory
    )
    app.add_middleware(RequestIdMiddleware)

    wire_shared(app, settings)
    # >>> example: tournaments
    wire_tournaments(app, settings)
    # <<< example: tournaments

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
