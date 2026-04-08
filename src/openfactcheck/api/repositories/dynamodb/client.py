# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false
"""boto3 DynamoDB table resource factory."""

from __future__ import annotations

from typing import Any

import boto3


def get_table(table_name: str, region_name: str = "us-east-1") -> Any:  # noqa: ANN401
    """Return a boto3 DynamoDB Table resource."""
    resource = boto3.resource("dynamodb", region_name=region_name)
    return resource.Table(table_name)
