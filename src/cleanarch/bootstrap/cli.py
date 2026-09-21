"""Composition root for the command line: ``python -m cleanarch ...``.

The HTTP app wires ports with ``dependency_overrides`` and commits through a
middleware. Here the same ports are built by hand and each command runs inside
``transaction()``. Two entrypoints, one application.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch import __version__
from cleanarch.bootstrap.events import build_event_bus
from cleanarch.bootstrap.logging import configure_logging
from cleanarch.bootstrap.settings import Settings, get_settings
from cleanarch.shared.application.actor import Actor
from cleanarch.shared.application.errors import ApplicationError
from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.infrastructure.clock import SystemClock
from cleanarch.shared.infrastructure.database import (
    make_engine,
    make_session_factory,
    transaction,
)
from cleanarch.shared.infrastructure.events import CollectedEvents

# isort: split
# >>> example: tournaments
from cleanarch.tournaments import cli as tournaments_cli
from cleanarch.tournaments.infrastructure.sqlalchemy import SqlAlchemyTournamentRepository

# <<< example: tournaments

OPERATOR = Actor(id="cli", roles=frozenset({"admin"}))
"""Whoever has shell access is trusted: the CLI runs as an admin."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleanarch", description="Clean Architecture template CLI"
    )
    parser.add_argument("--version", action="version", version=__version__)
    # >>> example: tournaments
    features = parser.add_subparsers(dest="feature", required=True)
    tournaments_cli.register(features)
    # <<< example: tournaments
    return parser


async def _dispatch(args: argparse.Namespace, settings: Settings) -> None:
    if settings.use_in_memory:
        raise SystemExit("DATABASE_URL=memory:// keeps nothing between commands; use a database.")
    engine = make_engine(settings.database_url, echo=settings.database_echo)
    events = CollectedEvents()
    try:
        # Same unit of work as an HTTP request: transaction, then events after commit.
        async with transaction(make_session_factory(engine)) as session:
            await _run_feature(args, session, events)
        await build_event_bus().dispatch(events.drain())
    finally:
        await engine.dispose()


async def _run_feature(
    args: argparse.Namespace, session: AsyncSession, events: CollectedEvents
) -> None:
    """One branch per feature: build its ports on the shared session, run the command."""
    feature = getattr(args, "feature", None)
    # >>> example: tournaments
    if feature == "tournaments":
        ports = tournaments_cli.Ports(
            repository=SqlAlchemyTournamentRepository(session),
            events=events,
            clock=SystemClock(),
            actor=OPERATOR,
        )
        await tournaments_cli.run(args, ports)
        return
    # <<< example: tournaments
    raise SystemExit(f"no feature registered for {feature!r}")


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    configure_logging("WARNING", settings.log_format)
    args = build_parser().parse_args(argv)
    try:
        asyncio.run(_dispatch(args, settings))
    except (DomainError, ApplicationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
