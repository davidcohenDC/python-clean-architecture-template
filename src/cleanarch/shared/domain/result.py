from collections.abc import Sequence
from dataclasses import dataclass

from cleanarch.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True)
class DomainResult[T]:
    """The outcome of a state-changing domain operation: new state + events.

    Aggregates here are immutable, so a method such as
    ``Order.submit()`` cannot mutate ``self`` and append to an internal
    event list. It returns a ``DomainResult`` instead::

        result = order.submit()
        result.aggregate   # the new Order
        result.events      # (OrderSubmitted(...),)

    Use cases persist ``aggregate`` and publish ``events``. Nothing else needs
    to know how events are collected.
    """

    aggregate: T
    events: Sequence[DomainEvent] = ()

    @classmethod
    def of(cls, aggregate: T, *events: DomainEvent) -> "DomainResult[T]":
        return cls(aggregate, tuple(events))
