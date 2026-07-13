"""Instant-run endpoint — stream a pipeline's events over HTTP.

A client POSTs a pipeline and receives the run's events as newline-delimited JSON (one event per
line), ending with a ``finished`` event. The run executes in-process and streams as it happens;
nothing is persisted, because an instant run is ephemeral. Batch dataset evaluation is a separate
subsystem and does not share this endpoint.
"""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from openfactcheck.api.crypto.protocols import SecretCipher
from openfactcheck.api.dependencies import (
    get_cipher,
    get_current_user,
    get_secret_repo,
    get_workspace_repo,
)
from openfactcheck.api.errors import AppError, ErrorCode, NotFoundError
from openfactcheck.api.models import AuthUser
from openfactcheck.api.repositories.constants import MAX_PIPELINE_BYTES
from openfactcheck.api.repositories.protocols import SecretRepository, WorkspaceRepository

router = APIRouter(prefix="/projects/{project_id}/workspaces/{workspace_id}", tags=["runs"])

ResourceId = Annotated[str, Path(max_length=20)]

_RUN_TIMEOUT_SECONDS = 300

# A run swaps the user's secrets into the process environment, so only one may run at a time.
_run_lock = asyncio.Lock()


class RunRequest(BaseModel):
    """Request body for running a pipeline."""

    pipeline: dict[str, object]


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


async def _stream_ndjson(pipeline: dict[str, object], secrets: dict[str, str]) -> AsyncIterator[str]:
    """Run the pipeline in-process, yielding each event as one JSON line, ending with a ``finished`` event.

    The user's decrypted secrets are swapped into the process environment for the run and restored
    afterward, with a lock serialising runs so one run's keys never overlap another's.
    """
    from openfactcheck.engine.events import FinishedEvent  # noqa: PLC0415 - lazy import keeps the engine optional.
    from openfactcheck.engine.executor import stream_pipeline  # noqa: PLC0415 - lazy import keeps the engine optional.

    async with _run_lock:
        saved = dict(os.environ)
        os.environ.update(secrets)
        events = stream_pipeline(pipeline)
        try:
            async with asyncio.timeout(_RUN_TIMEOUT_SECONDS):
                async for event in events:
                    yield event.model_dump_json() + "\n"
        except TimeoutError:
            timed_out = FinishedEvent(success=False, output="", error="Pipeline run timed out")
            yield timed_out.model_dump_json() + "\n"
        finally:
            await events.aclose()
            os.environ.clear()
            os.environ.update(saved)


@router.post("/run")
async def run_pipeline(  # noqa: PLR0913 - FastAPI DI requires all params as function args.
    project_id: ResourceId,
    workspace_id: ResourceId,
    body: RunRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    secret_repo: Annotated[SecretRepository, Depends(get_secret_repo)],
    cipher: Annotated[SecretCipher, Depends(get_cipher)],
) -> StreamingResponse:
    """Run a pipeline and stream its events as newline-delimited JSON.

    The response body is a stream of JSON events, one per line, ending with a ``finished`` event that
    carries the run's success and final output.
    """
    if len(json.dumps(body.pipeline).encode()) > MAX_PIPELINE_BYTES:
        raise AppError("Pipeline exceeds size limit", ErrorCode.VALIDATION_ERROR, status=422)
    if await repo.get(user.sub, project_id, workspace_id) is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")

    secrets = await _decrypt_secrets(secret_repo, cipher, user.sub, project_id)
    return StreamingResponse(_stream_ndjson(body.pipeline, secrets), media_type="application/x-ndjson")
