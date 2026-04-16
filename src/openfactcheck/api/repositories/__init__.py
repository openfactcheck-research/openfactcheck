"""Repository layer — data access protocols and implementations."""

from openfactcheck.api.repositories.protocols import (
    ProjectRepository,
    WorkspaceRepository,
)

__all__ = [
    "ProjectRepository",
    "WorkspaceRepository",
]
