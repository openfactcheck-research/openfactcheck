"""Encryption for user secret values, with cloud (KMS) and local backends."""

from openfactcheck.api.crypto.protocols import SecretCipher

__all__ = ["SecretCipher"]
