"""Tests for Cognito JWT verification and dev bypass."""

import time
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from openfactcheck.api.auth.cognito import DEV_USER, CognitoVerifier, DevVerifier
from openfactcheck.api.errors import AuthError

REGION = "us-east-1"
USER_POOL_ID = "us-east-1_TestPool"
CLIENT_ID = "test-client-id"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"


@pytest.fixture
def rsa_key() -> rsa.RSAPrivateKey:
    """Generate an RSA private key for signing test tokens."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def mock_jwk_client(rsa_key: rsa.RSAPrivateKey) -> MagicMock:
    """Return a mock PyJWKClient that resolves to the test RSA public key."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_key.public_key()

    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = mock_signing_key
    return client


@pytest.fixture
def verifier(mock_jwk_client: MagicMock) -> CognitoVerifier:
    return CognitoVerifier(REGION, USER_POOL_ID, CLIENT_ID, jwk_client=mock_jwk_client)


def _make_token(key: rsa.RSAPrivateKey, claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT with sensible defaults."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": "user-123",
        "email": "test@example.com",
        "name": "Test User",
        "token_use": "id",
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "iat": now,
        "exp": now + 3600,
    }
    if claims:
        payload.update(claims)

    private_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    return jwt.encode(payload, private_pem, algorithm="RS256")


# =============================================================================
# DevVerifier
# =============================================================================


def test_DevVerifier_verify() -> None:
    """DevVerifier returns the hardcoded dev user for any token."""
    dev_verifier = DevVerifier()

    user = dev_verifier.verify("anything")

    assert user == DEV_USER
    assert user.sub == "dev-user-00000000"
    assert user.email == "dev@localhost"


def test_DevVerifier_verify_empty_token() -> None:
    """DevVerifier works even with an empty token string."""
    dev_verifier = DevVerifier()

    user = dev_verifier.verify("")

    assert user == DEV_USER


# =============================================================================
# CognitoVerifier — valid token
# =============================================================================


def test_CognitoVerifier_verify_valid_token(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier returns AuthUser from a valid ID token."""
    token = _make_token(rsa_key)

    user = verifier.verify(token)

    assert user.sub == "user-123"
    assert user.email == "test@example.com"
    assert user.name == "Test User"


def test_CognitoVerifier_verify_missing_name(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier defaults name to empty string when absent."""
    token = _make_token(rsa_key, {"name": None})

    user = verifier.verify(token)

    assert user.name == ""


# =============================================================================
# CognitoVerifier — error cases
# =============================================================================


def test_CognitoVerifier_verify_expired_token(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier raises AuthError for an expired token."""
    token = _make_token(rsa_key, {"exp": int(time.time()) - 3600})

    with pytest.raises(AuthError, match="Invalid or expired token"):
        verifier.verify(token)


def test_CognitoVerifier_verify_wrong_audience(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier raises AuthError when audience doesn't match."""
    token = _make_token(rsa_key, {"aud": "wrong-client-id"})

    with pytest.raises(AuthError, match="Invalid or expired token"):
        verifier.verify(token)


def test_CognitoVerifier_verify_wrong_issuer(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier raises AuthError when issuer doesn't match."""
    token = _make_token(rsa_key, {"iss": "https://evil.example.com"})

    with pytest.raises(AuthError, match="Invalid or expired token"):
        verifier.verify(token)


def test_CognitoVerifier_verify_access_token_rejected(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier raises AuthError when token_use is 'access' instead of 'id'."""
    token = _make_token(rsa_key, {"token_use": "access"})

    with pytest.raises(AuthError, match="not an ID token"):
        verifier.verify(token)


def test_CognitoVerifier_verify_missing_sub(verifier: CognitoVerifier, rsa_key: rsa.RSAPrivateKey) -> None:
    """CognitoVerifier raises AuthError when sub claim is missing."""
    token = _make_token(rsa_key, {"sub": None})

    with pytest.raises(AuthError, match="Invalid or expired token"):
        verifier.verify(token)


def test_CognitoVerifier_verify_garbage_token() -> None:
    """CognitoVerifier raises AuthError for a completely invalid token string."""
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = jwt.InvalidTokenError("bad")
    bad_verifier = CognitoVerifier(REGION, USER_POOL_ID, CLIENT_ID, jwk_client=mock_client)

    with pytest.raises(AuthError, match="Invalid or expired token"):
        bad_verifier.verify("not.a.jwt")
