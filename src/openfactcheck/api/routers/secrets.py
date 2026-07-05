"""User secret management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from openfactcheck.api.crypto.protocols import SecretCipher
from openfactcheck.api.dependencies import get_cipher, get_current_user, get_secret_repo
from openfactcheck.api.errors import NotFoundError, SecretLimitError
from openfactcheck.api.models import AuthUser
from openfactcheck.api.models.secret import SECRET_NAME_PATTERN
from openfactcheck.api.repositories.protocols import SecretRepository
from openfactcheck.api.schemas.secrets import SecretResponse, SetSecretRequest

router = APIRouter(prefix="/secrets", tags=["secrets"])

SecretName = Annotated[str, Path(pattern=SECRET_NAME_PATTERN, max_length=64)]

_MIN_HINT_LENGTH = 8
"""Shortest value length for which a trailing hint is revealed."""


@router.get("/")
async def list_secrets(
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[SecretRepository, Depends(get_secret_repo)],
) -> list[SecretResponse]:
    """List the user's stored secrets, without their values."""
    secrets = await repo.list(user.sub)
    return [SecretResponse.from_model(s) for s in secrets]


@router.put("/{name}")
async def set_secret(
    name: SecretName,
    body: SetSecretRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[SecretRepository, Depends(get_secret_repo)],
    cipher: Annotated[SecretCipher, Depends(get_cipher)],
) -> SecretResponse:
    """Set or replace a secret's value. The value is encrypted and never returned."""
    ciphertext = await cipher.encrypt(body.value, context={"user_id": user.sub})
    # Reveal the last four characters as a hint, only when the value is long enough not to over-reveal it.
    hint = body.value[-4:] if len(body.value) >= _MIN_HINT_LENGTH else ""
    secret = await repo.set(user.sub, name, ciphertext, hint)
    if secret is None:
        raise SecretLimitError
    return SecretResponse.from_model(secret)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    name: SecretName,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[SecretRepository, Depends(get_secret_repo)],
) -> None:
    """Delete a secret."""
    deleted = await repo.delete(user.sub, name)
    if not deleted:
        raise NotFoundError(f"Secret '{name}' not found")
