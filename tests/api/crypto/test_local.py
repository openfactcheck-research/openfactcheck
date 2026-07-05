"""Tests for LocalCipher."""

import stat
from pathlib import Path

import pytest

from openfactcheck.api.crypto.local import LocalCipher

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_LocalCipher_encrypt_decrypt_round_trip(tmp_path: Path) -> None:
    """Decrypting an encrypted value returns the original, and the ciphertext differs from it."""
    cipher = LocalCipher(str(tmp_path / "secrets.key"))

    ciphertext = await cipher.encrypt("sk-secret-value", context={"user_id": "u1"})
    plaintext = await cipher.decrypt(ciphertext, context={"user_id": "u1"})

    assert ciphertext != "sk-secret-value"
    assert plaintext == "sk-secret-value"


async def test_LocalCipher_persists_key_with_owner_only_permissions(tmp_path: Path) -> None:
    """The key file is written with 0600 permissions and reused by a fresh instance."""
    key_path = tmp_path / "secrets.key"
    ciphertext = await LocalCipher(str(key_path)).encrypt("value", context={"user_id": "u1"})

    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert await LocalCipher(str(key_path)).decrypt(ciphertext, context={"user_id": "u1"}) == "value"
