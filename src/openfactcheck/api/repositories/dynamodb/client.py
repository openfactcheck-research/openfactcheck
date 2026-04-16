"""boto3 DynamoDB table resource factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


def get_table(table_name: str, region_name: str = "us-east-1") -> Table:
    """Return a boto3 DynamoDB Table resource."""

    resource: DynamoDBServiceResource = boto3.resource(
        "dynamodb",
        region_name=region_name,
    )

    return resource.Table(table_name)
