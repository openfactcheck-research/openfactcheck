"""Run request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from openfactcheck.api.models import Run


class CreateRunRequest(BaseModel):
    """Body for POST /api/v1/projects/{pid}/runs."""

    workspace_id: str = Field(max_length=20)
    pipeline: dict[str, object]


class RunResponse(BaseModel):
    """Single run in API responses."""

    id: str
    project_id: str
    workspace_id: str
    status: str
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_model(run: Run) -> "RunResponse":
        """Convert a domain Run to a response schema."""
        return RunResponse(
            id=run.id,
            project_id=run.project_id,
            workspace_id=run.workspace_id,
            status=run.status.value,
            output=run.output,
            error=run.error,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
