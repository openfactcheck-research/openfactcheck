"""Request parameters for Serper.dev search."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

type SerperTimeRange = Literal["qdr:h", "qdr:d", "qdr:w", "qdr:m", "qdr:y"]
"""Recency window for results: past hour, day, week, month, or year."""


class SearchParams(BaseModel):
    """Parameters for a Serper.dev search request.

    Only ``q`` is required. Unset fields are dropped from the request body so
    the service applies its own defaults.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    q: str
    """The search query."""

    gl: str | None = None
    """Country code for results, such as ``us``."""

    hl: str | None = None
    """Language code for results, such as ``en``."""

    location: str | None = None
    """Location to search from, such as ``SoHo, New York, United States``."""

    num: int | None = None
    """Number of results to return."""

    page: int | None = None
    """Result page number, starting at 1."""

    tbs: SerperTimeRange | None = None
    """Restrict results to a recent time window."""

    autocorrect: bool | None = None
    """Whether the service may autocorrect the query spelling."""

    def to_payload(self) -> dict[str, object]:
        """Render the request body, omitting unset fields.

        Returns:
            A JSON-serialisable mapping of the parameters that were set.
        """
        return self.model_dump(exclude_none=True)
