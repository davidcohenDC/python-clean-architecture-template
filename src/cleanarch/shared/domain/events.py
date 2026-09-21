import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Something that happened in the domain, expressed in past tense.

    Events are immutable facts. They carry only primitive data so that any
    adapter (logger, message broker, webhook...) can serialise them without
    knowing the domain model.

    ``event_id`` and ``occurred_at`` are metadata: two events with the same
    payload are *equal* even if they were raised at different times. That is
    what makes ``assert result.events == (OrderSubmitted(id),)`` possible.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex, compare=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), compare=False)
