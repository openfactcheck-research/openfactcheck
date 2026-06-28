"""Preferences request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from openfactcheck.api.models import Preferences

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class UpdatePreferencesRequest(BaseModel):
    """Input payload for replacing a user's preferences."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    tour_completed: bool = False
    """Whether the user has finished the welcome tour."""


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class PreferencesResponse(BaseModel):
    """A user's preferences returned in API responses."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    tour_completed: bool
    """Whether the user has finished the welcome tour."""

    @staticmethod
    def from_model(preferences: Preferences) -> PreferencesResponse:
        """Convert a domain ``Preferences`` to a response schema."""
        return PreferencesResponse(tour_completed=preferences.tour_completed)
