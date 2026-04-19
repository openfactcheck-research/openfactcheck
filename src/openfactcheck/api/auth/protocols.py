"""Token verifier protocol for bearer-token auth implementations."""

from typing import Protocol

from openfactcheck.api.models import AuthUser


class TokenVerifier(Protocol):
    """Interface for verifying an Authorization bearer token.

    Implementations validate a bearer token and return the authenticated
    user, or raise if the token is invalid.
    """

    def verify(self, token: str) -> AuthUser:
        """Verify a bearer token and return the authenticated user.

        Args:
            token: The raw token string from the Authorization header.

        Returns:
            The authenticated user.

        Raises:
            AuthError: If the token is invalid, expired, or missing required claims.
        """
        ...
