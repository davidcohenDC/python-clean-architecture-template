"""Everything the tournaments example needs from the outside world (EXAMPLE)."""

import argparse
import logging

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch.bootstrap.settings import Settings
from cleanarch.bootstrap.transaction import Session
from cleanarch.shared.application.actor import OPERATOR
from cleanarch.shared.infrastructure.clock import SystemClock
from cleanarch.shared.infrastructure.events import CollectedEvents, InProcessEventBus
from cleanarch.tournaments import cli
from cleanarch.tournaments.application import TournamentRepository
from cleanarch.tournaments.domain import TournamentStarted
from cleanarch.tournaments.http import get_tournament_repository, router
from cleanarch.tournaments.infrastructure.in_memory import InMemoryTournamentRepository
from cleanarch.tournaments.infrastructure.sqlalchemy import SqlAlchemyTournamentRepository

logger = logging.getLogger(__name__)


def wire_http(app: FastAPI, settings: Settings) -> None:
    if settings.use_in_memory:
        repository = InMemoryTournamentRepository()
        app.dependency_overrides[get_tournament_repository] = lambda: repository
    else:

        def sqlalchemy_repository(session: Session) -> TournamentRepository:
            return SqlAlchemyTournamentRepository(session)

        app.dependency_overrides[get_tournament_repository] = sqlalchemy_repository
    app.include_router(router, prefix="/api/v1")


def subscribe(bus: InProcessEventBus) -> None:
    async def announce(event: TournamentStarted) -> None:
        # Example subscriber. Replace with e-mail, webhook, broker... or delete.
        logger.info("Tournament %s is live!", event.tournament_id)

    bus.subscribe(TournamentStarted, announce)


def register_cli(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    cli.register(subparsers)


async def run_cli(args: argparse.Namespace, session: AsyncSession, events: CollectedEvents) -> bool:
    if getattr(args, "feature", None) != "tournaments":
        return False
    ports = cli.Ports(
        repository=SqlAlchemyTournamentRepository(session),
        events=events,
        clock=SystemClock(),
        actor=OPERATOR,
    )
    await cli.run(args, ports)
    return True
