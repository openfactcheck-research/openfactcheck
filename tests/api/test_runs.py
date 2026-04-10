"""Tests for run endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

PROJECTS_BASE = "/api/v1/projects"

SAMPLE_PIPELINE: dict[str, Any] = {
    "blocks": {
        "blocks": [
            {
                "type": "text_print",
                "id": "print-1",
                "inputs": {
                    "TEXT": {
                        "block": {
                            "type": "text",
                            "id": "text-1",
                            "fields": {"TEXT": "Hello World"},
                        },
                    },
                },
            },
        ],
    },
}


async def _create_project(client: AsyncClient, name: str = "Test Project") -> str:
    response = await client.post(f"{PROJECTS_BASE}/", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _create_workspace(client: AsyncClient, project_id: str, name: str = "Test WS") -> str:
    response = await client.post(f"{PROJECTS_BASE}/{project_id}/workspaces/", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _runs_base(project_id: str) -> str:
    return f"{PROJECTS_BASE}/{project_id}/runs"


async def _create_run(client: AsyncClient, project_id: str, workspace_id: str) -> dict[str, Any]:
    response = await client.post(
        f"{_runs_base(project_id)}/",
        json={"workspace_id": workspace_id, "pipeline": SAMPLE_PIPELINE},
    )
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# POST /runs
# ---------------------------------------------------------------------------


async def test_create_run(client: AsyncClient) -> None:
    """POST creates a run with pending status and returns 201."""
    pid = await _create_project(client)
    wid = await _create_workspace(client, pid)

    body = await _create_run(client, pid, wid)

    assert body["project_id"] == pid
    assert body["workspace_id"] == wid
    assert body["status"] == "pending"
    assert body["output"] is None
    assert body["error"] is None


async def test_create_run_executes_locally(client: AsyncClient) -> None:
    """Run executes in background and completes with output."""
    pid = await _create_project(client)
    wid = await _create_workspace(client, pid)

    body = await _create_run(client, pid, wid)
    run_id = body["id"]

    # Give the background task time to complete
    await asyncio.sleep(0.1)

    response = await client.get(f"{_runs_base(pid)}/{run_id}")
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "completed"
    assert result["output"] == "Hello World"
    assert result["error"] is None
    assert result["started_at"] is not None
    assert result["completed_at"] is not None


# ---------------------------------------------------------------------------
# GET /runs/{run_id}
# ---------------------------------------------------------------------------


async def test_get_run(client: AsyncClient) -> None:
    """GET returns a run by ID."""
    pid = await _create_project(client)
    wid = await _create_workspace(client, pid)
    created = await _create_run(client, pid, wid)

    response = await client.get(f"{_runs_base(pid)}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_run_not_found(client: AsyncClient) -> None:
    """GET returns 404 for nonexistent run."""
    pid = await _create_project(client)

    response = await client.get(f"{_runs_base(pid)}/does-not-exist")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /runs
# ---------------------------------------------------------------------------


async def test_list_runs(client: AsyncClient) -> None:
    """GET /runs lists all runs for a project."""
    pid = await _create_project(client)
    wid = await _create_workspace(client, pid)
    await _create_run(client, pid, wid)
    await _create_run(client, pid, wid)

    response = await client.get(f"{_runs_base(pid)}/")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_runs_empty(client: AsyncClient) -> None:
    """GET /runs returns empty list when no runs exist."""
    pid = await _create_project(client)

    response = await client.get(f"{_runs_base(pid)}/")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_runs_filter_by_workspace(client: AsyncClient) -> None:
    """GET /runs?workspace_id= filters by workspace."""
    pid = await _create_project(client)
    wid1 = await _create_workspace(client, pid, "WS 1")
    wid2 = await _create_workspace(client, pid, "WS 2")
    await _create_run(client, pid, wid1)
    await _create_run(client, pid, wid2)

    response = await client.get(f"{_runs_base(pid)}/", params={"workspace_id": wid1})

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["workspace_id"] == wid1
