"""Tests for the pipeline run endpoint (local isolated-subprocess execution)."""

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

PROJECTS_BASE = "/api/v1/projects"


async def _make_workspace(client: AsyncClient) -> tuple[str, str]:
    project_id = (await client.post(f"{PROJECTS_BASE}/", json={"name": "P"})).json()["id"]
    workspace_id = (await client.post(f"{PROJECTS_BASE}/{project_id}/workspaces/", json={"name": "W"})).json()["id"]
    return project_id, workspace_id


async def _poll_run(client: AsyncClient, project_id: str, workspace_id: str) -> dict[str, Any]:
    url = f"{PROJECTS_BASE}/{project_id}/workspaces/{workspace_id}/run"
    for _ in range(200):
        run = (await client.get(url)).json()
        if run and run["status"] in {"completed", "failed"}:
            return run
        await asyncio.sleep(0.05)
    raise AssertionError("run did not finish in time")


async def test_run_executes_pipeline_in_isolated_subprocess(client: AsyncClient) -> None:
    project_id, workspace_id = await _make_workspace(client)
    pipeline = {
        "blocks": {"blocks": [{"type": "text_print", "inputs": {"TEXT": {"block": {"type": "text", "fields": {"TEXT": "hi"}}}}}]},
    }

    response = await client.post(
        f"{PROJECTS_BASE}/{project_id}/workspaces/{workspace_id}/run",
        json={"pipeline": pipeline},
    )

    assert response.status_code == 202
    run = await _poll_run(client, project_id, workspace_id)
    assert run["status"] == "completed"
    assert run["output"] == "hi"
