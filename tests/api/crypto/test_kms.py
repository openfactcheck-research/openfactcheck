"""Tests for KmsCipher (moto-mocked KMS)."""

import pytest

from openfactcheck.api.crypto.kms import KmsCipher

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_KmsCipher_encrypt_decrypt_round_trip(kms_cipher: KmsCipher) -> None:
    """Decrypting a KMS-encrypted value returns the original, and the ciphertext differs from it."""
    ciphertext = await kms_cipher.encrypt("sk-secret-value")
    plaintext = await kms_cipher.decrypt(ciphertext)

    assert ciphertext != "sk-secret-value"
    assert plaintext == "sk-secret-value"
