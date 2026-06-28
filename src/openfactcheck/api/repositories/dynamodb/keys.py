"""DynamoDB single-table key composition with PK + SK.

Table design:
    PK (hash key): partition key, groups related items.
    SK (sort key): distinguishes entity types within a partition.

Project keys:
    PK: USER#<userId>
    SK: PROJECT#<projectId>

Workspace keys:
    PK: USER#<userId>#PROJECT#<projectId>
    SK: WORKSPACE#<workspaceId>

Run keys:
    PK: USER#<userId>#PROJECT#<projectId>
    SK: WORKSPACE#<workspaceId>

Secret keys:
    PK: USER#<userId>
    SK: SECRET#<name>

Preferences keys:
    PK: USER#<userId>
    SK: PREFERENCES
"""

# ---------------------------------------------------------------------------
# Project keys
# ---------------------------------------------------------------------------


def project_pk(user_id: str) -> str:
    """Partition key grouping all projects for a user."""
    return f"USER#{user_id}"


def project_sk(project_id: str) -> str:
    """Sort key for a specific project."""
    return f"PROJECT#{project_id}"


# ---------------------------------------------------------------------------
# Workspace keys
# ---------------------------------------------------------------------------


def workspace_pk(user_id: str, project_id: str) -> str:
    """Partition key grouping all workspaces (and their runs) within a project."""
    return f"USER#{user_id}#PROJECT#{project_id}"


def workspace_sk(workspace_id: str) -> str:
    """Sort key for a specific workspace."""
    return f"WORKSPACE#{workspace_id}"


# ---------------------------------------------------------------------------
# Secret keys
# ---------------------------------------------------------------------------


def secret_pk(user_id: str) -> str:
    """Partition key grouping all secrets for a user."""
    return f"USER#{user_id}"


def secret_sk(name: str) -> str:
    """Sort key for a specific secret."""
    return f"SECRET#{name}"


# ---------------------------------------------------------------------------
# Preferences keys
# ---------------------------------------------------------------------------


def preferences_pk(user_id: str) -> str:
    """Partition key for a user's preferences."""
    return f"USER#{user_id}"


def preferences_sk() -> str:
    """Sort key for the user's single preferences record."""
    return "PREFERENCES"
