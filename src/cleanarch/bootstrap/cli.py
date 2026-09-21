"""Composition root for the command line: ``python -m cleanarch ...``.

The HTTP app wires ports with ``dependency_overrides`` and commits through a
middleware. Here the same ports are built by hand and each command runs inside
``transaction()``, with events dispatched after the commit. Two entrypoints,
one application; features add their commands through ``bootstrap/features``.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch import __version__
from cleanarch.bootstrap.events import build_event_bus
from cleanarch.bootstrap.features import FEATURES
from cleanarch.bootstrap.logging import configure_logging
from cleanarch.bootstrap.settings import Settings, get_settings
from cleanarch.shared.application.errors import ApplicationError
from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.infrastructure.database import (
    make_engine,
    make_session_factory,
    transaction,
)
from cleanarch.shared.infrastructure.events import CollectedEvents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleanarch", description="Every feature adds its commands here."
    )
    parser.add_argument("--version", action="version", version=__version__)
    features = parser.add_subparsers(dest="feature")
    for feature in FEATURES:
        if register := getattr(feature, "register_cli", None):
            register(features)
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
    for feature in FEATURES:
        run = getattr(feature, "run_cli", None)
        if run and await run(args, session, events):
            return
    raise SystemExit(f"no feature handles {getattr(args, 'feature', None)!r}; see --help")


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    configure_logging("WARNING", settings.log_format)
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "feature", None) is None:
        parser.print_help()
        return 2
    try:
        asyncio.run(_dispatch(args, settings))
    except (DomainError, ApplicationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
