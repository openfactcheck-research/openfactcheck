"""Tests for KmsCipher (moto-mocked KMS)."""

import pytest
from botocore.exceptions import ClientError

from openfactcheck.api.crypto.kms import KmsCipher

pytestmark = pytest.mark.asyncio(loop_scope="function")

CONTEXT = {"user_id": "user-1"}


async def test_KmsCipher_encrypt_decrypt_round_trip(kms_cipher: KmsCipher) -> None:
    """Decrypting with the same context returns the original; the ciphertext differs from it."""
    ciphertext = await kms_cipher.encrypt("sk-secret-value", context=CONTEXT)
    plaintext = await kms_cipher.decrypt(ciphertext, context=CONTEXT)

    assert ciphertext != "sk-secret-value"
    assert plaintext == "sk-secret-value"


async def test_KmsCipher_decrypt_wrong_context_fails(kms_cipher: KmsCipher) -> None:
    """A ciphertext bound to one owner's context cannot be decrypted under another's."""
    ciphertext = await kms_cipher.encrypt("sk-secret-value", context=CONTEXT)

    with pytest.raises(ClientError):
        await kms_cipher.decrypt(ciphertext, context={"user_id": "someone-else"})
