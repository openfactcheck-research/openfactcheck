"""Tests for project CRUD endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

BASE = "/api/v1/projects"


async def _create_project(client: AsyncClient, name: str = "Test Project") -> dict[str, object]:
    response = await client.post(BASE, json={"name": name})
    assert response.status_code == 201
    return response.json()


async def test_create_project(client: AsyncClient) -> None:
    """POST /projects creates a project and returns 201."""
    body = await _create_project(client, "My Project")

    assert body["name"] == "My Project"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_list_projects(client: AsyncClient) -> None:
    """GET /projects returns all projects for the user."""
    await _create_project(client, "First")
    await _create_project(client, "Second")

    response = await client.get(BASE)

    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 2
    assert projects[0]["name"] == "First"
    assert projects[1]["name"] == "Second"


async def test_list_projects_empty(client: AsyncClient) -> None:
    """GET /projects returns an empty list when no projects exist."""
    response = await client.get(BASE)

    assert response.status_code == 200
    assert response.json() == []


async def test_get_project(client: AsyncClient) -> None:
    """GET /projects/{id} returns the project."""
    created = await _create_project(client)

    response = await client.get(f"{BASE}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_project_not_found(client: AsyncClient) -> None:
    """GET /projects/{id} returns 404 for a non-existent project."""
    response = await client.get(f"{BASE}/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"


async def test_update_project(client: AsyncClient) -> None:
    """PATCH /projects/{id} updates the project name."""
    created = await _create_project(client, "Old Name")

    response = await client.patch(f"{BASE}/{created['id']}", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


async def test_update_project_not_found(client: AsyncClient) -> None:
    """PATCH /projects/{id} returns 404 for a non-existent project."""
    response = await client.patch(f"{BASE}/does-not-exist", json={"name": "X"})

    assert response.status_code == 404


async def test_delete_project(client: AsyncClient) -> None:
    """DELETE /projects/{id} removes the project and returns 204."""
    created = await _create_project(client)

    response = await client.delete(f"{BASE}/{created['id']}")

    assert response.status_code == 204

    get_response = await client.get(f"{BASE}/{created['id']}")
    assert get_response.status_code == 404


async def test_delete_project_not_found(client: AsyncClient) -> None:
    """DELETE /projects/{id} returns 404 for a non-existent project."""
    response = await client.delete(f"{BASE}/does-not-exist")

    assert response.status_code == 404


async def test_create_project_empty_name(client: AsyncClient) -> None:
    """POST /projects with an empty name returns 422."""
    response = await client.post(BASE, json={"name": ""})

    assert response.status_code == 422
