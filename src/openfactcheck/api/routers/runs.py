"""Run endpoints — /api/v1/projects/{project_id}/runs."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from openfactcheck.api.config import APIConfig
from openfactcheck.api.dependencies import get_config, get_current_user, get_run_repo
from openfactcheck.api.errors import AppError, ErrorCode, NotFoundError
from openfactcheck.api.models import AuthUser, RunCreate, RunStatus
from openfactcheck.api.repositories.constants import MAX_PIPELINE_BYTES
from openfactcheck.api.repositories.protocols import RunRepository
from openfactcheck.api.schemas.runs import CreateRunRequest, RunResponse

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])

ResourceId = Annotated[str, Path(max_length=20)]


async def _execute_and_update(
    repo: RunRepository, user_id: str, project_id: str, run_id: str, pipeline: dict[str, object]
) -> None:
    """Background task: run the pipeline and update the run record."""
    from openfactcheck.engine import execute_pipeline

    await repo.update_status(user_id, project_id, run_id, RunStatus.RUNNING)
    result = await execute_pipeline(pipeline)
    if result.success:
        await repo.update_status(user_id, project_id, run_id, RunStatus.COMPLETED, output=result.output)
    else:
        await repo.update_status(
            user_id, project_id, run_id, RunStatus.FAILED, output=result.output, error=result.error
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_run(
    project_id: ResourceId,
    body: CreateRunRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[RunRepository, Depends(get_run_repo)],
    config: Annotated[APIConfig, Depends(get_config)],
) -> RunResponse:
    """Create and execute a new pipeline run."""
    pipeline_size = len(json.dumps(body.pipeline).encode())
    if pipeline_size > MAX_PIPELINE_BYTES:
        raise AppError("Pipeline exceeds size limit", ErrorCode.VALIDATION_ERROR, status=422)

    run = await repo.create(user.sub, project_id, RunCreate(workspace_id=body.workspace_id, pipeline=body.pipeline))

    if config.mode == "cloud":
        # TODO: push SQS message for executor Lambda (Phase 1g)
        pass
    else:
        asyncio.create_task(_execute_and_update(repo, user.sub, project_id, run.id, body.pipeline))

    return RunResponse.from_model(run)


@router.get("/{run_id}")
async def get_run(
    project_id: ResourceId,
    run_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[RunRepository, Depends(get_run_repo)],
) -> RunResponse:
    """Get a single run by ID."""
    run = await repo.get(user.sub, project_id, run_id)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    return RunResponse.from_model(run)


@router.get("/")
async def list_runs(
    project_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[RunRepository, Depends(get_run_repo)],
    workspace_id: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RunResponse]:
    """List runs for a project, optionally filtered by workspace."""
    runs = await repo.list_by_project(user.sub, project_id, workspace_id=workspace_id, limit=limit, offset=offset)
    return [RunResponse.from_model(r) for r in runs]
