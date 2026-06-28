"""User preferences domain model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from openfactcheck.api.models.validators import to_camel


class Preferences(BaseModel):
    """Account-level user preferences.

    A single record per user. Unset fields take their defaults, so a user with
    no stored preferences reads as an all-default record.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        use_attribute_docstrings=True,
    )

    tour_completed: bool = False
    """Whether the user has finished the welcome tour."""
