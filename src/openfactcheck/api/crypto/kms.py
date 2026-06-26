"""AWS KMS-backed secret cipher for cloud deployments."""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_kms.client import KMSClient


class KmsCipher:
    """Encrypts secret values with a KMS customer-managed key.

    Each value is encrypted directly with the key. KMS accepts plaintext up to
    4 KB, well beyond any API key, so no envelope key management is needed. The
    ciphertext is base64-encoded for storage as a plain string.
    """

    def __init__(self, key_id: str, region_name: str = "us-east-1") -> None:
        """Build a cipher bound to a KMS key.

        Args:
            key_id: Identifier or ARN of the KMS customer-managed key.
            region_name: AWS region the key lives in.
        """
        self._key_id = key_id
        self._client: KMSClient = boto3.client("kms", region_name=region_name)

    async def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret value into a base64-encoded ciphertext."""

        def _do() -> str:
            response = self._client.encrypt(KeyId=self._key_id, Plaintext=plaintext.encode())
            return base64.b64encode(response["CiphertextBlob"]).decode()

        return await asyncio.to_thread(_do)

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext back to its secret value."""

        def _do() -> str:
            response = self._client.decrypt(KeyId=self._key_id, CiphertextBlob=base64.b64decode(ciphertext))
            return response["Plaintext"].decode()

        return await asyncio.to_thread(_do)
