"""Token verifier protocol — interface for all auth implementations."""

from typing import Protocol

from openfactcheck.api.models import AuthUser


class TokenVerifier(Protocol):
    """Interface for verifying an Authorization bearer token."""

    def verify(self, token: str) -> AuthUser: ...
