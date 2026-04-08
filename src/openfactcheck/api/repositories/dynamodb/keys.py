"""DynamoDB single-table key composition — mirrors the frontend key scheme.

Table design:
    PK (hash key)  — unique item identifier
    GS1PK (GSI)    — query key for listing items by parent

Project keys:
    PK:    USER#<userId>#PROJECT#<projectId>
    GS1PK: USER#<userId>

Workspace keys:
    PK:    USER#<userId>#PROJECT#<projectId>#WORKSPACE#<workspaceId>
    GS1PK: USER#<userId>#PROJECT#<projectId>
"""

from __future__ import annotations


def project_pk(user_id: str, project_id: str) -> str:
    """Primary key for a project item."""
    return f"USER#{user_id}#PROJECT#{project_id}"


def project_gs1pk(user_id: str) -> str:
    """GSI key to list all projects for a user."""
    return f"USER#{user_id}"


def workspace_pk(user_id: str, project_id: str, workspace_id: str) -> str:
    """Primary key for a workspace item."""
    return f"USER#{user_id}#PROJECT#{project_id}#WORKSPACE#{workspace_id}"


def workspace_gs1pk(user_id: str, project_id: str) -> str:
    """GSI key to list all workspaces for a project."""
    return f"USER#{user_id}#PROJECT#{project_id}"
