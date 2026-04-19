"""DynamoDB table resource helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


def get_table(table_name: str, region_name: str = "us-east-1") -> Table:
    """Return a handle to the named DynamoDB table in the given AWS region."""
    resource: DynamoDBServiceResource = boto3.resource(
        "dynamodb",
        region_name=region_name,
    )

    return resource.Table(table_name)
