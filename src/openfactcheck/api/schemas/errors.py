"""Error response schema."""

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """JSON body returned for all API errors."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    detail: str
    """Human-readable error message."""

    code: str
    """Machine-readable error code for clients."""

    status: int
    """HTTP status code."""
