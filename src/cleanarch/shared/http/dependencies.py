"""Dependency *declarations* for ports that every feature may need.

These functions are placeholders: routers depend on them, and the
composition root (``cleanarch.bootstrap``) overrides them with real
providers via ``app.dependency_overrides``. Tests override them with fakes
the same way. See ADR-003.
"""

from cleanarch.shared.application.ports import EventPublisher


def get_event_publisher() -> EventPublisher:
    raise NotImplementedError("Provided by cleanarch.bootstrap (dependency_overrides)")
