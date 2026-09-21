"""The event bus and its subscribers, shared by the HTTP app and the CLI."""

from cleanarch.bootstrap.features import FEATURES
from cleanarch.shared.infrastructure.events import InProcessEventBus


def build_event_bus() -> InProcessEventBus:
    bus = InProcessEventBus()
    for feature in FEATURES:
        if subscribe := getattr(feature, "subscribe", None):
            subscribe(bus)
    return bus
