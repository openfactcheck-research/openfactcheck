"""Tests for the pipeline run endpoint (HTTP newline-delimited JSON streaming)."""

import json
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

PROJECTS_BASE = "/api/v1/projects"

# A pipeline of one print block: it needs no API keys, so it runs fully offline.
_PRINT_PIPELINE = {
    "blocks": {
        "blocks": [
            {"type": "text_print", "inputs": {"TEXT": {"block": {"type": "text", "fields": {"TEXT": "hi"}}}}},
        ],
    },
}


async def _make_workspace(client: AsyncClient) -> tuple[str, str]:
    project_id = (await client.post(PROJECTS_BASE, json={"name": "P"})).json()["id"]
    workspace_id = (await client.post(f"{PROJECTS_BASE}/{project_id}/workspaces", json={"name": "W"})).json()["id"]
    return project_id, workspace_id


def _events(body: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


async def test_run_streams_events_as_ndjson(client: AsyncClient) -> None:
    """A run streams its events as newline-delimited JSON, ending with a successful finished event."""
    project_id, workspace_id = await _make_workspace(client)

    response = await client.post(
        f"{PROJECTS_BASE}/{project_id}/workspaces/{workspace_id}/run",
        json={"pipeline": _PRINT_PIPELINE},
    )

    assert response.status_code == 200
    events = _events(response.text)
    assert any(e["type"] == "output" and e["text"] == "hi" for e in events)
    assert events[-1] == {"type": "finished", "success": True, "output": "hi", "error": None}


async def test_run_unknown_workspace_returns_404(client: AsyncClient) -> None:
    """A run against a nonexistent workspace is a 404 before any streaming begins."""
    project_id = (await client.post(PROJECTS_BASE, json={"name": "P"})).json()["id"]

    response = await client.post(
        f"{PROJECTS_BASE}/{project_id}/workspaces/missing/run",
        json={"pipeline": _PRINT_PIPELINE},
    )

    assert response.status_code == 404
