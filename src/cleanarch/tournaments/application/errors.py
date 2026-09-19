from cleanarch.shared.application.errors import NotFoundError


class TournamentNotFound(NotFoundError):
    message = "Tournament not found."

    def __init__(self, tournament_id: str) -> None:
        super().__init__(f"Tournament '{tournament_id}' not found.")
