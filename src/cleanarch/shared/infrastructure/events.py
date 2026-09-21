"""In-process events: collected during the unit of work, dispatched after commit.

Two small pieces:

* ``CollectedEvents`` implements the ``EventPublisher`` port. ``publish`` only
  *records* events; nothing runs yet. One instance per unit of work (per HTTP
  request, per CLI command).
* ``InProcessEventBus`` holds the handlers. The composition root calls
  ``dispatch`` with the collected events **after the transaction committed**.

Semantics (ADR-005):

* handlers run after commit, sequentially, in publication order, in-process;
* a handler that reads the database sees the committed state;
* if the unit of work rolls back, its events are dropped and no handler runs;
* a failing handler is logged and does not fail the request (the state is
  already committed - reporting an error would lie to the client) nor stop
  the other handlers;
* delivery is at-most-once: if the process dies between commit and dispatch
  the events are lost. That is the gap an outbox fills, when you need it.
"""

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from cleanarch.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class CollectedEvents:
    """``EventPublisher`` that remembers what was published until the unit of work ends."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        self._events.extend(events)

    def drain(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events


class InProcessEventBus:
    def __init__(self) -> None:
        self._handlers: defaultdict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe[E: DomainEvent](
        self, event_type: type[E], handler: Callable[[E], Awaitable[None]]
    ) -> None:
        """Handlers are typed on the concrete event; mypy checks the pairing at the call site."""
        self._handlers[event_type].append(handler)

    async def dispatch(self, events: Sequence[DomainEvent]) -> None:
        """Run every handler for every event, in order. Failures are logged, not raised."""
        for event in events:
            logger.info("event %s %s", type(event).__name__, event)
            for handler in self._handlers.get(type(event), ()):
                try:
                    await handler(event)
                except Exception:
                    logger.exception(
                        "event handler %s failed for %s", handler.__qualname__, type(event).__name__
                    )
