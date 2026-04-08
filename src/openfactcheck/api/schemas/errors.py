"""Error response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """JSON body returned for all API errors."""

    detail: str
    code: str
    status: int
