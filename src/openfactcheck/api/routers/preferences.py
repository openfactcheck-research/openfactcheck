"""User preferences endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from openfactcheck.api.dependencies import get_current_user, get_preferences_repo
from openfactcheck.api.models import AuthUser, Preferences
from openfactcheck.api.repositories.protocols import PreferencesRepository
from openfactcheck.api.schemas.preferences import PreferencesResponse, UpdatePreferencesRequest

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("")
async def get_preferences(
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[PreferencesRepository, Depends(get_preferences_repo)],
) -> PreferencesResponse:
    """Return the current user's preferences."""
    preferences = await repo.get(user.sub)
    return PreferencesResponse.from_model(preferences)


@router.put("")
async def update_preferences(
    body: UpdatePreferencesRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[PreferencesRepository, Depends(get_preferences_repo)],
) -> PreferencesResponse:
    """Replace the current user's preferences."""
    preferences = await repo.set(user.sub, Preferences(tour_completed=body.tour_completed))
    return PreferencesResponse.from_model(preferences)
