"""Dev bypass verifier that returns the same user on every call, without validating the token."""

from openfactcheck.api.models import AuthUser

DEV_USER = AuthUser(
    sub="dev-user-00000000",
    email="dev@localhost",
    name="Dev User",
)
"""User returned by [`DevVerifier`][DevVerifier] on every call."""


class DevVerifier:
    """Bypass verifier for local development.

    Returns [`DEV_USER`][DEV_USER] on every call, without validating the token.

    Warning:
        Never use in production.
    """

    def verify(self, token: str) -> AuthUser:
        """Return the dev user regardless of the token value.

        Args:
            token: Ignored; present only to match the verifier protocol.

        Returns:
            The [`DEV_USER`][DEV_USER] constant on every call.
        """
        return DEV_USER
