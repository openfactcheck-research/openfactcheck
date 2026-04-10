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
    SK: RUN#<runId>

GSI keys:
    GS1PK: USER#<userId>                                           — list projects
    GS2PK: USER#<userId>#PROJECT#<projectId>#WORKSPACE#<wsId>      — list runs by workspace
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


def project_gs1pk(user_id: str) -> str:
    """GSI key to list all projects for a user."""
    return f"USER#{user_id}"


# ---------------------------------------------------------------------------
# Workspace keys
# ---------------------------------------------------------------------------


def workspace_pk(user_id: str, project_id: str) -> str:
    """Partition key for workspace items — groups all children of a project."""
    return f"USER#{user_id}#PROJECT#{project_id}"


def workspace_sk(workspace_id: str) -> str:
    """Sort key for a specific workspace."""
    return f"WORKSPACE#{workspace_id}"


# ---------------------------------------------------------------------------
# Run keys
# ---------------------------------------------------------------------------


def run_pk(user_id: str, project_id: str) -> str:
    """Partition key for run items — same partition as workspaces (project children)."""
    return f"USER#{user_id}#PROJECT#{project_id}"


def run_sk(run_id: str) -> str:
    """Sort key for a specific run."""
    return f"RUN#{run_id}"


def run_gs2pk(user_id: str, project_id: str, workspace_id: str) -> str:
    """GSI key to list all runs for a workspace."""
    return f"USER#{user_id}#PROJECT#{project_id}#WORKSPACE#{workspace_id}"
