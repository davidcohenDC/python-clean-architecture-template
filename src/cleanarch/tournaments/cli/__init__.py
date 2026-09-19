"""CLI adapter for tournaments: a second *driving* adapter next to ``http/``.

It calls the same use cases through the same ports. Nothing in ``application``
or ``domain`` knows whether a request came from HTTP or from a terminal.
"""

from cleanarch.tournaments.cli.commands import Ports, register, run

__all__ = ["Ports", "register", "run"]
