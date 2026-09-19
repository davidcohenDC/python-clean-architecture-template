from cleanarch.shared.domain.errors import DomainError


class InvalidTournamentName(DomainError):
    message = "Tournament name must be 1-100 non-blank characters."


class InvalidPhases(DomainError):
    message = "Tournament phases are inconsistent."


class TournamentAlreadyStarted(DomainError):
    message = "Tournament has already started."


class TournamentNotStarted(DomainError):
    message = "Tournament has not started yet."


class TournamentAlreadyFinished(DomainError):
    message = "Tournament is already finished."
