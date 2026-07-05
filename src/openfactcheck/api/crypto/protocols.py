"""Protocol for encrypting secret values at the storage boundary."""

from collections.abc import Mapping
from typing import Protocol


class SecretCipher(Protocol):
    """Encrypts and decrypts user secret values.

    An implementation sits between the secret repository and the stored
    ciphertext: a value is encrypted before it is written and decrypted only
    when a run needs it. The backing key material never leaves the
    implementation, so callers handle plaintext and opaque ciphertext only.

    The ``context`` binds a ciphertext to the identity that owns it. The same
    context supplied at encrypt time must be supplied at decrypt time, so a
    ciphertext for one owner cannot be decrypted under another's context.
    """

    async def encrypt(self, plaintext: str, *, context: Mapping[str, str]) -> str:
        """Encrypt a secret value.

        Args:
            plaintext: The raw secret value.
            context: Key-value pairs bound to the ciphertext; the same pairs are
                required to decrypt it.

        Returns:
            Opaque ciphertext, safe to persist in the database.
        """
        ...

    async def decrypt(self, ciphertext: str, *, context: Mapping[str, str]) -> str:
        """Decrypt a stored ciphertext back to its secret value.

        Args:
            ciphertext: Ciphertext produced when the value was encrypted.
            context: The same key-value pairs supplied when the value was
                encrypted; decryption fails if they do not match.

        Returns:
            The original plaintext value.
        """
        ...
