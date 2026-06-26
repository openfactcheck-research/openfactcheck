# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Shared fixtures for cipher tests — moto-mocked KMS key."""

import os
from collections.abc import AsyncIterator

import boto3
import pytest_asyncio
from moto import mock_aws

from openfactcheck.api.crypto.kms import KmsCipher

REGION = "us-east-1"


@pytest_asyncio.fixture(loop_scope="function")
async def kms_cipher() -> AsyncIterator[KmsCipher]:
    """Yield a KmsCipher bound to a fresh moto-mocked KMS key."""
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"

        client = boto3.client("kms", region_name=REGION)
        key = client.create_key()
        yield KmsCipher(key["KeyMetadata"]["KeyId"], REGION)
