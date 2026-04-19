"""Authenticated user model derived from JWT claims."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthUser:
    """Current authenticated user, extracted from a Cognito JWT."""

    sub: str
    """Cognito user pool subject identifier."""

    email: str
    """User's verified email address."""

    name: str = ""
    """User's display name. May be empty when the identity provider doesn't supply one."""
