# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for engine secret resolution (moto-mocked DynamoDB + KMS)."""

import base64
from collections.abc import Callable, Iterator

import boto3
import pytest
from moto import mock_aws

from openfactcheck.engine.secrets import resolve_user_secrets

REGION = "us-east-1"
TABLE = "openfactcheck-users-test"

SecretWriter = Callable[[str, str, str], None]


@pytest.fixture
def put_secret(monkeypatch: pytest.MonkeyPatch) -> Iterator[SecretWriter]:
    """Yield a helper that stores a KMS-encrypted secret in a moto users table."""
    with mock_aws():
        monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

        kms = boto3.client("kms", region_name=REGION)
        key_id = kms.create_key()["KeyMetadata"]["KeyId"]

        ddb = boto3.client("dynamodb", region_name=REGION)
        ddb.create_table(
            TableName=TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        monkeypatch.setenv("OPENFACTCHECK_DYNAMODB_USERS_TABLE_NAME", TABLE)
        monkeypatch.setenv("OPENFACTCHECK_SECRETS_KMS_KEY_ID", key_id)
        monkeypatch.setenv("OPENFACTCHECK_DYNAMODB_REGION", REGION)

        table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)

        def _put(user_id: str, name: str, value: str) -> None:
            blob = kms.encrypt(KeyId=key_id, Plaintext=value.encode())["CiphertextBlob"]
            table.put_item(
                Item={
                    "PK": f"USER#{user_id}",
                    "SK": f"SECRET#{name}",
                    "name": name,
                    "ciphertext": base64.b64encode(blob).decode(),
                },
            )

        yield _put


def test_resolve_user_secrets_round_trip(put_secret: SecretWriter) -> None:
    put_secret("u1", "OPENAI_API_KEY", "sk-test-value")

    assert resolve_user_secrets("u1") == {"OPENAI_API_KEY": "sk-test-value"}


def test_resolve_user_secrets_multiple(put_secret: SecretWriter) -> None:
    put_secret("u1", "OPENAI_API_KEY", "sk-1")
    put_secret("u1", "SERPER_API_KEY", "serper-2")

    assert resolve_user_secrets("u1") == {"OPENAI_API_KEY": "sk-1", "SERPER_API_KEY": "serper-2"}


def test_resolve_user_secrets_empty(put_secret: SecretWriter) -> None:
    assert resolve_user_secrets("nobody") == {}


def test_resolve_user_secrets_scoped_to_user(put_secret: SecretWriter) -> None:
    put_secret("u1", "OPENAI_API_KEY", "sk-1")

    assert resolve_user_secrets("u2") == {}
