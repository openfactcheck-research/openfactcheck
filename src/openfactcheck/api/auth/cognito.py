"""Cognito JWT verification against a user pool's JWKS."""

import jwt
from jwt import PyJWKClient

from openfactcheck.api.errors import AuthError
from openfactcheck.api.models import AuthUser


class CognitoVerifier:
    """Verify Cognito ID tokens against a user pool's JWKS.

    Validates the RS256 signature, expiration, issuer, audience, and the
    ``token_use=id`` claim. Returns the authenticated user or raises
    [`AuthError`][AuthError] on any failure.
    """

    def __init__(
        self,
        region: str,
        user_pool_id: str,
        client_id: str,
        *,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        """Build a verifier bound to a specific Cognito user pool.

        Args:
            region: AWS region of the user pool, e.g. ``"us-east-1"``.
            user_pool_id: Cognito user pool identifier.
            client_id: App client identifier that tokens must be issued to.
            jwk_client: JWK client to use. Typically omitted so the verifier
                creates its own from the pool's JWKS endpoint; inject a
                custom one in tests.
        """
        self._issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._client_id = client_id
        self._jwk_client = jwk_client or PyJWKClient(f"{self._issuer}/.well-known/jwks.json")

    def verify(self, token: str) -> AuthUser:
        """Decode and validate a Cognito ID token.

        Args:
            token: The raw JWT string as received from the client.

        Returns:
            The authenticated user, populated from the token's ``sub``,
            ``email``, and ``name`` claims.

        Raises:
            AuthError: If the token is invalid, expired, not an ID token,
                or missing required claims.
        """
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
