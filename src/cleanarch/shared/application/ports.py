"""Ports shared by every feature.

A *port* is an interface owned by the inside (application layer) and
implemented by the outside (infrastructure). We use ``typing.Protocol`` so an
adapter never has to inherit from anything: if it has the right methods, it
fits. That also keeps test fakes trivial.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from cleanarch.shared.domain.events import DomainEvent


class EventPublisher(Protocol):
    """Outbound port: hand domain events to whoever is interested.

    The application layer does not know (or care) whether the implementation
    logs them, dispatches them in-process or pushes them to a broker.
    """

    async def publish(self, events: Sequence[DomainEvent]) -> None: ...


class Clock(Protocol):
    """Outbound port: the current time.

    Use cases never call ``datetime.now()``: they ask the clock and pass the
    value into the domain. Tests inject a fixed clock and get deterministic
    timestamps for free.
    """

    def now(self) -> datetime: ...
