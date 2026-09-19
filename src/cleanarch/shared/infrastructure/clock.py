"""``Clock`` port implementations."""

from datetime import UTC, datetime


class SystemClock:
    """The real wall clock, always timezone-aware UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that returns whatever you tell it. Handy in tests and demos."""

    def __init__(self, at: datetime) -> None:
        self.at = at

    def now(self) -> datetime:
        return self.at
