"""DynamoDB single-table key composition with PK + SK.

Table design:
    PK (hash key)  — partition key, groups related items
    SK (sort key)  — distinguishes entity types within a partition

Project keys:
    PK: USER#<userId>
    SK: PROJECT#<projectId>

Workspace keys:
    PK: USER#<userId>#PROJECT#<projectId>
    SK: WORKSPACE#<workspaceId>

Run keys:
    PK: USER#<userId>#PROJECT#<projectId>
    SK: WORKSPACE#<workspaceId>
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Project keys
# ---------------------------------------------------------------------------


def project_pk(user_id: str) -> str:
    """Partition key for project items — groups all projects for a user."""
    return f"USER#{user_id}"


def project_sk(project_id: str) -> str:
    """Sort key for a specific project."""
    return f"PROJECT#{project_id}"


# ---------------------------------------------------------------------------
# Workspace keys
# ---------------------------------------------------------------------------


def workspace_pk(user_id: str, project_id: str) -> str:
    """Partition key for workspace items — groups all children of a project."""
    return f"USER#{user_id}#PROJECT#{project_id}"


def workspace_sk(workspace_id: str) -> str:
    """Sort key for a specific workspace."""
    return f"WORKSPACE#{workspace_id}"
