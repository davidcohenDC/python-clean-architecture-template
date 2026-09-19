"""Domain building blocks: errors, events and the ``DomainResult`` wrapper."""

from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.domain.result import DomainResult

__all__ = ["DomainError", "DomainEvent", "DomainResult"]
