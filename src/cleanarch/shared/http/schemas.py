from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    """Base class for every request/response model.

    ``extra="forbid"`` makes typos in client payloads a 422 instead of a silent
    no-op. ``from_attributes`` lets ``Model.model_validate(domain_obj)`` work.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ErrorResponse(Schema):
    """Uniform error envelope returned by every handler in ``errors.py``."""

    error: str = Field(description="Machine-readable error type, e.g. OrderNotFound")
    message: str = Field(description="Human-readable explanation")
