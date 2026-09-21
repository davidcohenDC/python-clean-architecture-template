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


class ForbiddenError(ApplicationError):
    """The actor is authenticated but not allowed to do this."""

    message = "Not allowed."


class ConflictError(ApplicationError):
    """The change was based on stale state: someone else modified it first.

    Raised by repositories on ``save`` (optimistic concurrency, see ADR-010).
    The client should reload and retry.
    """

    message = "The resource was modified concurrently; reload and retry."
