"""Inputs of the use cases.

Only ``CreateTournament`` needs a command object: it carries several fields.
Use cases that take a single id accept it directly (see ``use_cases.py``) -
a command class per use case would be ceremony without benefit.
"""

from dataclasses import dataclass

from cleanarch.tournaments.domain import Phases


@dataclass(frozen=True, slots=True)
class CreateTournamentCommand:
    name: str
    phases: Phases
