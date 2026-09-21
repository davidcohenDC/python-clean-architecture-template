"""The event bus and its subscribers, shared by the HTTP app and the CLI."""

import logging

from cleanarch.shared.infrastructure.events import InProcessEventBus

# isort: split
# >>> example: tournaments
from cleanarch.tournaments.domain import TournamentStarted

# <<< example: tournaments

logger = logging.getLogger(__name__)


def build_event_bus() -> InProcessEventBus:
    bus = InProcessEventBus()
    # >>> example: tournaments

    async def announce(event: TournamentStarted) -> None:
        # Example subscriber. Replace with e-mail, webhook, broker... or delete.
        logger.info("Tournament %s is live!", event.tournament_id)

    bus.subscribe(TournamentStarted, announce)
    # <<< example: tournaments
    return bus
