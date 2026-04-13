"""Authenticated user model derived from JWT claims."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthUser:
    """Current authenticated user, extracted from a Cognito JWT.

    Attributes:
        sub: Cognito user pool subject identifier (used as user_id throughout the API).
        email: User's verified email address.
        name: User's display name (may be empty).
    """

    sub: str
    email: str
    name: str = ""
