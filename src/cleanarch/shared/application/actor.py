"""Who is performing a request, as the inside sees it.

The HTTP adapter authenticates (API key, JWT, session...) and produces an
``Actor``. Use cases receive it and decide what the actor may do. Neither the
domain nor the use cases ever see a token.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Actor:
    id: str
    roles: frozenset[str] = frozenset()

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


ANONYMOUS = Actor(id="anonymous")
"""The actor used when authentication is disabled (no API keys configured)."""

OPERATOR = Actor(id="operator", roles=frozenset({"admin"}))
"""Whoever has shell access: the CLI runs as this admin."""
