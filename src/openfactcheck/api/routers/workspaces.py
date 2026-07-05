"""Workspace CRUD and pipeline-run endpoints."""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from openfactcheck.api.config import APIConfig
from openfactcheck.api.crypto.protocols import SecretCipher
from openfactcheck.api.dependencies import (
    get_cipher,
    get_config,
    get_current_user,
    get_secret_repo,
    get_workspace_repo,
)
from openfactcheck.api.errors import (
    AppError,
    ErrorCode,
    NotFoundError,
    WorkspaceLimitError,
)
from openfactcheck.api.models import (
    AuthUser,
    WorkspaceCreate,
    WorkspaceRun,
    WorkspaceRunStatus,
    WorkspaceUpdate,
)
from openfactcheck.api.repositories.constants import (
    MAX_CONTENT_BYTES,
    MAX_PIPELINE_BYTES,
)
from openfactcheck.api.repositories.protocols import SecretRepository, WorkspaceRepository
from openfactcheck.api.schemas.workspaces import (
    CreateWorkspaceRequest,
    ReorderWorkspacesRequest,
    UpdateWorkspaceRequest,
    WorkspaceResponse,
)

router = APIRouter(prefix="/projects/{project_id}/workspaces", tags=["workspaces"])

_background_tasks: set[asyncio.Task[None]] = set()

ResourceId = Annotated[str, Path(max_length=20)]


@router.get("/")
async def list_workspaces(
    project_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> list[WorkspaceResponse]:
    """List all workspaces in a project."""
    workspaces = await repo.list_by_project(user.sub, project_id)
    return [WorkspaceResponse.from_model(ws) for ws in workspaces]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    project_id: ResourceId,
    body: CreateWorkspaceRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Create a new workspace in a project."""
    ws = await repo.create(
        user.sub,
        project_id,
        WorkspaceCreate(name=body.name, description=body.description),
    )
    if ws is None:
        raise WorkspaceLimitError
    return WorkspaceResponse.from_model(ws)


@router.get("/{workspace_id}")
async def get_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Get a single workspace by ID."""
    ws = await repo.get(user.sub, project_id, workspace_id)
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    return WorkspaceResponse.from_model(ws)


@router.patch("/{workspace_id}")
async def update_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    body: UpdateWorkspaceRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Update a workspace."""
    if body.content is not None and len(str(body.content)) > MAX_CONTENT_BYTES:
        raise AppError(
            "Workspace content exceeds size limit",
            ErrorCode.VALIDATION_ERROR,
            status=422,
        )
    ws = await repo.update(
        user.sub,
        project_id,
        workspace_id,
        WorkspaceUpdate(
            name=body.name,
            description=body.description,
            locked=body.locked,
            settings=body.settings,
            content=body.content,
        ),
    )
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    return WorkspaceResponse.from_model(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> None:
    """Delete a workspace."""
    deleted = await repo.delete(user.sub, project_id, workspace_id)
    if not deleted:
        raise NotFoundError(f"Workspace {workspace_id} not found")


@router.post("/{workspace_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Duplicate a workspace."""
    # Check if source exists before attempting duplicate
    source = await repo.get(user.sub, project_id, workspace_id)
    if source is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")

    ws = await repo.duplicate(user.sub, project_id, workspace_id)
    if ws is None:
        raise WorkspaceLimitError
    return WorkspaceResponse.from_model(ws)


@router.put("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_workspaces(
    project_id: ResourceId,
    body: ReorderWorkspacesRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> None:
    """Reorder workspaces in a project. ordered_ids must be a complete permutation."""
    current = await repo.list_by_project(user.sub, project_id)
    current_ids = {ws.id for ws in current}
    submitted_ids = set(body.ordered_ids)

    if len(body.ordered_ids) != len(submitted_ids):
        raise AppError("ordered_ids contains duplicates", ErrorCode.VALIDATION_ERROR, status=422)
    if submitted_ids != current_ids:
        raise AppError(
            "ordered_ids must contain exactly all workspace IDs",
            ErrorCode.VALIDATION_ERROR,
            status=422,
        )

    await repo.reorder(user.sub, project_id, body.ordered_ids)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Request body for running a pipeline."""

    pipeline: dict[str, object]


class RunResponse(BaseModel):
    """Run state returned to the frontend."""

    status: str
    output: str = ""
    error: str = ""


async def _start_sfn(
    state_machine_arn: str,
    user_id: str,
    project_id: str,
    workspace_id: str,
    pipeline: dict[str, object],
) -> None:
    """Start a Step Functions execution for the pipeline."""
    import boto3  # noqa: PLC0415 - lazy import for optional cloud dependency.

    def _start() -> None:
        sfn = boto3.client("stepfunctions")
        sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(
                {
                    "user_id": user_id,
                    "project_id": project_id,
                    "workspace_id": workspace_id,
                    "pipeline": pipeline,
                },
            ),
        )

    await asyncio.to_thread(_start)


_RUN_TIMEOUT_SECONDS = 300


async def _decrypt_secrets(
    secret_repo: SecretRepository,
    cipher: SecretCipher,
    user_id: str,
    project_id: str,
) -> dict[str, str]:
    """Decrypt the user's global secrets plus this project's overrides (project wins)."""
    secrets: dict[str, str] = {}
    for scope, context in (
        (None, {"user_id": user_id}),
        (project_id, {"user_id": user_id, "project_id": project_id}),
    ):
        for secret in await secret_repo.list(user_id, project_id=scope):
            ciphertext = await secret_repo.get_ciphertext(user_id, secret.name, project_id=scope)
            if ciphertext is not None:
                secrets[secret.name] = await cipher.decrypt(ciphertext, context=context)
    return secrets


def _result_to_run(stdout: bytes, stderr: bytes) -> WorkspaceRun:
    """Build a run record from the engine subprocess output."""
    completed = datetime.now(UTC)
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        message = stderr.decode(errors="replace").strip() or "Pipeline execution failed"
        return WorkspaceRun(status=WorkspaceRunStatus.FAILED, error=message, completed_at=completed)
    output = str(data.get("output", ""))
    if data.get("success"):
        return WorkspaceRun(status=WorkspaceRunStatus.COMPLETED, output=output, completed_at=completed)
    return WorkspaceRun(
        status=WorkspaceRunStatus.FAILED,
        output=output,
        error=str(data.get("error") or "Pipeline execution failed"),
        completed_at=completed,
    )


async def _run_local(  # noqa: PLR0913 - distinct collaborators, each needed for the isolated run.
    repo: WorkspaceRepository,
    secret_repo: SecretRepository,
    cipher: SecretCipher,
    user_id: str,
    project_id: str,
    workspace_id: str,
    pipeline: dict[str, object],
) -> None:
    """Local mode: run the pipeline in an isolated subprocess and store the result.

    The subprocess environment is the base environment plus this user's
    decrypted secrets, so one run's API keys never leak into another's.
    """
    secrets = await _decrypt_secrets(secret_repo, cipher, user_id, project_id)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "openfactcheck.engine",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **secrets},
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(json.dumps(pipeline).encode()),
            timeout=_RUN_TIMEOUT_SECONDS,
        )
        run = _result_to_run(stdout, stderr)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        run = WorkspaceRun(
            status=WorkspaceRunStatus.FAILED,
            error="Pipeline run timed out",
            completed_at=datetime.now(UTC),
        )
    await repo.set_run(user_id, project_id, workspace_id, run)


@router.post("/{workspace_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(  # noqa: PLR0913 - FastAPI DI requires all params as function args.
    project_id: ResourceId,
    workspace_id: ResourceId,
    body: RunRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    secret_repo: Annotated[SecretRepository, Depends(get_secret_repo)],
    cipher: Annotated[SecretCipher, Depends(get_cipher)],
    config: Annotated[APIConfig, Depends(get_config)],
) -> RunResponse:
    """Run a pipeline. Sets workspace run to running and starts execution."""
    pipeline_size = len(json.dumps(body.pipeline).encode())
    if pipeline_size > MAX_PIPELINE_BYTES:
        raise AppError("Pipeline exceeds size limit", ErrorCode.VALIDATION_ERROR, status=422)

    ws = await repo.get(user.sub, project_id, workspace_id)
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")

    if config.mode == "cloud":
        try:
            await _start_sfn(
                config.state_machine_arn,
                user.sub,
                project_id,
                workspace_id,
                body.pipeline,
            )
        except Exception:
            run = WorkspaceRun(status=WorkspaceRunStatus.FAILED, error="Failed to dispatch pipeline")
            await repo.set_run(user.sub, project_id, workspace_id, run)
            raise
    else:
        run = WorkspaceRun(status=WorkspaceRunStatus.RUNNING, started_at=datetime.now(UTC))
        await repo.set_run(user.sub, project_id, workspace_id, run)
        task = asyncio.create_task(
            _run_local(repo, secret_repo, cipher, user.sub, project_id, workspace_id, body.pipeline),
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return RunResponse(status="running")


@router.get("/{workspace_id}/run")
async def get_run(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> RunResponse | None:
    """Get the latest run state for a workspace."""
    ws = await repo.get(user.sub, project_id, workspace_id)
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    if ws.run is None:
        return None
    return RunResponse(status=ws.run.status, output=ws.run.output, error=ws.run.error)
