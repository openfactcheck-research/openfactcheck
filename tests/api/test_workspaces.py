"""Tests for workspace CRUD endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

PROJECTS_BASE = "/api/v1/projects"


async def _create_project(client: AsyncClient, name: str = "Test Project") -> str:
    response = await client.post(f"{PROJECTS_BASE}/", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _ws_base(project_id: str) -> str:
    return f"{PROJECTS_BASE}/{project_id}/workspaces"


async def _create_workspace(client: AsyncClient, project_id: str, name: str = "Test WS") -> dict[str, object]:
    response = await client.post(f"{_ws_base(project_id)}/", json={"name": name})
    assert response.status_code == 201
    return response.json()


async def test_create_workspace(client: AsyncClient) -> None:
    """POST creates a workspace and returns 201."""
    pid = await _create_project(client)

    body = await _create_workspace(client, pid, "My Workspace")

    assert body["name"] == "My Workspace"
    assert body["project_id"] == pid
    assert body["sort_order"] == 1
    assert body["locked"] is False


async def test_list_workspaces(client: AsyncClient) -> None:
    """GET returns all workspaces ordered by sort_order."""
    pid = await _create_project(client)
    await _create_workspace(client, pid, "First")
    await _create_workspace(client, pid, "Second")

    response = await client.get(f"{_ws_base(pid)}/")

    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 2
    assert workspaces[0]["name"] == "First"
    assert workspaces[1]["name"] == "Second"


async def test_list_workspaces_empty(client: AsyncClient) -> None:
    """GET returns an empty list when no workspaces exist."""
    pid = await _create_project(client)

    response = await client.get(f"{_ws_base(pid)}/")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_workspace(client: AsyncClient) -> None:
    """GET /{wid} returns the workspace."""
    pid = await _create_project(client)
    created = await _create_workspace(client, pid)

    response = await client.get(f"{_ws_base(pid)}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_workspace_not_found(client: AsyncClient) -> None:
    """GET /{wid} returns 404 for a non-existent workspace."""
    pid = await _create_project(client)

    response = await client.get(f"{_ws_base(pid)}/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


async def test_update_workspace(client: AsyncClient) -> None:
    """PATCH updates workspace fields."""
    pid = await _create_project(client)
    created = await _create_workspace(client, pid, "Old")

    response = await client.patch(
        f"{_ws_base(pid)}/{created['id']}",
        json={"name": "New", "description": "Updated", "locked": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New"
    assert body["description"] == "Updated"
    assert body["locked"] is True


async def test_update_workspace_not_found(client: AsyncClient) -> None:
    """PATCH returns 404 for a non-existent workspace."""
    pid = await _create_project(client)

    response = await client.patch(f"{_ws_base(pid)}/does-not-exist", json={"name": "X"})

    assert response.status_code == 404


async def test_delete_workspace(client: AsyncClient) -> None:
    """DELETE removes the workspace and returns 204."""
    pid = await _create_project(client)
    created = await _create_workspace(client, pid)

    response = await client.delete(f"{_ws_base(pid)}/{created['id']}")

    assert response.status_code == 204

    get_response = await client.get(f"{_ws_base(pid)}/{created['id']}")
    assert get_response.status_code == 404


async def test_delete_workspace_not_found(client: AsyncClient) -> None:
    """DELETE returns 404 for a non-existent workspace."""
    pid = await _create_project(client)

    response = await client.delete(f"{_ws_base(pid)}/does-not-exist")

    assert response.status_code == 404


async def test_duplicate_workspace(client: AsyncClient) -> None:
    """POST /{wid}/duplicate creates a copy."""
    pid = await _create_project(client)
    original = await _create_workspace(client, pid, "Original")

    response = await client.post(f"{_ws_base(pid)}/{original['id']}/duplicate")

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Original (copy)"
    assert body["id"] != original["id"]
    assert body["sort_order"] == 2


async def test_create_workspace_enforces_limit(client: AsyncClient) -> None:
    """POST returns 422 when workspace limit is reached."""
    pid = await _create_project(client)
    for i in range(5):
        await _create_workspace(client, pid, f"WS {i}")

    response = await client.post(f"{_ws_base(pid)}/", json={"name": "Overflow"})

    assert response.status_code == 422
    assert response.json()["code"] == "WORKSPACE_LIMIT_REACHED"


async def test_reorder_workspaces(client: AsyncClient) -> None:
    """PUT /reorder updates sort order."""
    pid = await _create_project(client)
    ws1 = await _create_workspace(client, pid, "A")
    ws2 = await _create_workspace(client, pid, "B")
    ws3 = await _create_workspace(client, pid, "C")

    response = await client.put(
        f"{_ws_base(pid)}/reorder",
        json={"ordered_ids": [ws3["id"], ws1["id"], ws2["id"]]},
    )

    assert response.status_code == 204

    list_response = await client.get(f"{_ws_base(pid)}/")
    names = [ws["name"] for ws in list_response.json()]
    assert names == ["C", "A", "B"]
