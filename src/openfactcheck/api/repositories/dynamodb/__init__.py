"""DynamoDB-backed repository implementations."""

from openfactcheck.api.repositories.dynamodb.projects import DynamoProjectRepository
from openfactcheck.api.repositories.dynamodb.workspaces import DynamoWorkspaceRepository

__all__ = [
    "DynamoProjectRepository",
    "DynamoWorkspaceRepository",
]
