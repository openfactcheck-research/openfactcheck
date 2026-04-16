"""Dev bypass verifier — always returns a fixed user, no token validation."""

from openfactcheck.api.models import AuthUser

DEV_USER = AuthUser(
    sub="dev-user-00000000",
    email="dev@localhost",
    name="Dev User",
)


class DevVerifier:
    """Bypass verifier for local development. Always returns a fixed dev user."""

    def verify(self, token: str) -> AuthUser:  # noqa: ARG002 - required by TokenVerifier protocol.
        """Return the hardcoded dev user regardless of the token value."""
        return DEV_USER
