"""Fernet-backed secret cipher for local development."""

from collections.abc import Mapping
from pathlib import Path

from cryptography.fernet import Fernet


class LocalCipher:
    """Encrypts secret values with a locally stored symmetric key.

    The key is generated on first use and persisted to a key file with
    owner-only permissions, so secrets encrypted in local mode survive across
    restarts. It exists because local mode has no KMS to call.
    """

    def __init__(self, key_path: str) -> None:
        """Build a cipher backed by a key file, creating the key if absent.

        Args:
            key_path: Path to the key file. A new key is written with mode
                ``0600`` when the file does not yet exist.
        """
        self._fernet = Fernet(self._load_or_create_key(key_path))

    @staticmethod
    def _load_or_create_key(key_path: str) -> bytes:
        """Read the key file, generating and persisting a new key when it is missing."""
        path = Path(key_path).expanduser()
        if path.exists():
            return path.read_bytes()
        key = Fernet.generate_key()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key)
        path.chmod(0o600)
        return key

    async def encrypt(self, plaintext: str, *, context: Mapping[str, str]) -> str:
        """Encrypt a secret value into a token string.

        The context is accepted for protocol parity but not bound; this cipher
        is for local development only, where the key file already scopes access.
        """
        return self._fernet.encrypt(plaintext.encode()).decode()

    async def decrypt(self, ciphertext: str, *, context: Mapping[str, str]) -> str:
        """Decrypt a token string back to its secret value.

        The context is accepted for protocol parity but not enforced.
        """
        return self._fernet.decrypt(ciphertext.encode()).decode()
