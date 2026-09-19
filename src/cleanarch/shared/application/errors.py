class ApplicationError(Exception):
    """Base class for errors raised by use cases (as opposed to domain rules).

    Typical subclasses: *not found*, *conflict*, *permission denied*.
    They describe a failed *request*, not a violated *business rule*.
    """

    message: str = "The request could not be fulfilled."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NotFoundError(ApplicationError):
    """The requested resource does not exist."""

    message = "Resource not found."
