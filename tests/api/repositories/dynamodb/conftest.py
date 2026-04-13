# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Shared fixtures for DynamoDB repository tests — moto-mocked table."""

import os
from collections.abc import AsyncIterator

import boto3
import pytest_asyncio
from moto import mock_aws

TABLE_NAME = "openfactcheck-test"
REGION = "us-east-1"


@pytest_asyncio.fixture(loop_scope="function")
async def dynamo_table() -> AsyncIterator[str]:
    """Create a moto-mocked DynamoDB table and yield its name."""
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"

        client = boto3.client("dynamodb", region_name=REGION)
        client.create_table(
            TableName=TABLE_NAME,
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

        yield TABLE_NAME
