"""Cognito JWT verification and dev bypass."""

from __future__ import annotations

from typing import Protocol

import jwt
from jwt import PyJWKClient

from openfactcheck.api.errors import AuthError
from openfactcheck.api.models import AuthUser


class TokenVerifier(Protocol):
    """Interface for verifying an Authorization bearer token."""

    def verify(self, token: str) -> AuthUser: ...


class CognitoVerifier:
    """Verify Cognito ID tokens using JWKS.

    Fetches the public keys from the Cognito user pool and validates:
    RS256 signature, expiration, issuer, audience, and token_use=id.
    """

    def __init__(
        self,
        region: str,
        user_pool_id: str,
        client_id: str,
        *,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self._issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._client_id = client_id
        self._jwk_client = jwk_client or PyJWKClient(f"{self._issuer}/.well-known/jwks.json")

    def verify(self, token: str) -> AuthUser:
        """Decode and validate a Cognito ID token, returning the authenticated user."""
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            payload: dict[str, object] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._client_id,
                options={"require": ["exp", "iss", "aud", "sub", "token_use"]},
            )
        except jwt.InvalidTokenError as e:
            raise AuthError("Invalid or expired token") from e

        if payload.get("token_use") != "id":
            raise AuthError("Token is not an ID token")

        sub = payload.get("sub")
        email = payload.get("email")
        if not isinstance(sub, str) or not isinstance(email, str):
            raise AuthError("Token missing required claims")

        name = payload.get("name", "")
        if not isinstance(name, str):
            name = ""

        return AuthUser(sub=sub, email=email, name=name)


DEV_USER = AuthUser(
    sub="dev-user-00000000",
    email="dev@localhost",
    name="Dev User",
)


class DevVerifier:
    """Bypass verifier for local development. Always returns a fixed dev user."""

    def verify(self, token: str) -> AuthUser:  # noqa: ARG002
        """Return the hardcoded dev user regardless of the token value."""
        return DEV_USER
