"""Tournament domain: pure Python, no framework, no I/O.

Everything here is a frozen dataclass. State changes return a *new* object
wrapped in ``DomainResult`` together with the events they produced.
"""

from cleanarch.tournaments.domain.errors import (
    InvalidPhases,
    InvalidTournamentName,
    TournamentAlreadyFinished,
    TournamentAlreadyStarted,
    TournamentNotStarted,
)
from cleanarch.tournaments.domain.events import (
    TournamentAdvanced,
    TournamentCreated,
    TournamentFinished,
    TournamentStarted,
)
from cleanarch.tournaments.domain.phases import (
    BracketPhase,
    Cut,
    Elimination,
    NoCut,
    PairingSystem,
    Phase,
    PhaseConfig,
    Phases,
    RoundPhase,
    TopCut,
)
from cleanarch.tournaments.domain.progress import Progress, TournamentStatus
from cleanarch.tournaments.domain.tournament import Tournament, TournamentId, new_tournament_id

__all__ = [
    "BracketPhase",
    "Cut",
    "Elimination",
    "InvalidPhases",
    "InvalidTournamentName",
    "NoCut",
    "PairingSystem",
    "Phase",
    "PhaseConfig",
    "Phases",
    "Progress",
    "RoundPhase",
    "TopCut",
    "Tournament",
    "TournamentAdvanced",
    "TournamentAlreadyFinished",
    "TournamentAlreadyStarted",
    "TournamentCreated",
    "TournamentFinished",
    "TournamentId",
    "TournamentNotStarted",
    "TournamentStarted",
    "TournamentStatus",
    "new_tournament_id",
]
