"""Protocol for encrypting secret values at the storage boundary."""

from typing import Protocol


class SecretCipher(Protocol):
    """Encrypts and decrypts user secret values.

    An implementation sits between the secret repository and the stored
    ciphertext: a value is encrypted before it is written and decrypted only
    when a run needs it. The backing key material never leaves the
    implementation, so callers handle plaintext and opaque ciphertext only.
    """

    async def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret value.

        Args:
            plaintext: The raw secret value.

        Returns:
            Opaque ciphertext, safe to persist in the database.
        """
        ...

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt a stored ciphertext back to its secret value.

        Args:
            ciphertext: Ciphertext produced when the value was encrypted.

        Returns:
            The original plaintext value.
        """
        ...
