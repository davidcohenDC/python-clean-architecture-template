class DomainError(Exception):
    """Base class for every rule violation raised by the domain.

    Subclass it per feature with a *specific* name (``TournamentAlreadyStarted``)
    instead of passing free-form messages around: the HTTP layer maps types to
    status codes, and tests assert on types, not on strings.
    """

    message: str = "Domain rule violated."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)
