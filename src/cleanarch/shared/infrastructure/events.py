"""In-process implementation of the ``EventPublisher`` port."""

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from cleanarch.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class InProcessEventBus:
    """Dispatch events to handlers registered for their type, synchronously.

    "Synchronously" means the use case awaits every handler before returning.
    That is the simplest correct behaviour for a template: no lost events, no
    background tasks to reason about. If a handler is slow or unreliable,
    that is the moment to introduce an outbox + broker (see docs/extending).
    """

    def __init__(self) -> None:
        self._handlers: defaultdict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe[E: DomainEvent](
        self, event_type: type[E], handler: Callable[[E], Awaitable[None]]
    ) -> None:
        """Handlers are typed on the concrete event; mypy checks the pairing at the call site."""
        self._handlers[event_type].append(handler)

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            logger.info("event %s %s", type(event).__name__, event)
            for handler in self._handlers.get(type(event), ()):
                await handler(event)
