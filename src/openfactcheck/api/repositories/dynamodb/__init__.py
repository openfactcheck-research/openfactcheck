"""DynamoDB repository implementations using boto3 with asyncio.to_thread."""

from openfactcheck.api.repositories.dynamodb.projects import DynamoProjectRepository
from openfactcheck.api.repositories.dynamodb.workspaces import DynamoWorkspaceRepository

__all__ = [
    "DynamoProjectRepository",
    "DynamoWorkspaceRepository",
]
