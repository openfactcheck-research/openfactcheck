# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""DynamoDB implementation of the run repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from openfactcheck.api.models import Run, RunCreate, RunStatus
from openfactcheck.api.repositories.constants import generate_id
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import run_gs2pk, run_pk, run_sk


def _item_to_model(item: dict[str, Any]) -> Run:
    return Run(
        id=item["id"],
        user_id=item["userId"],
        project_id=item["projectId"],
        workspace_id=item["workspaceId"],
        status=RunStatus(item["status"]),
        pipeline=item.get("pipeline", {}),
        output=item.get("output"),
        error=item.get("error"),
        started_at=datetime.fromisoformat(item["startedAt"]) if item.get("startedAt") else None,
        completed_at=datetime.fromisoformat(item["completedAt"]) if item.get("completedAt") else None,
        created_at=datetime.fromisoformat(item["createdAt"]),
        updated_at=datetime.fromisoformat(item["updatedAt"]),
    )


class DynamoRunRepository(BaseDynamoRepository):
    """Run CRUD backed by DynamoDB single-table design."""

    async def create(self, user_id: str, project_id: str, data: RunCreate) -> Run:
        now = datetime.now(UTC)
        rid = generate_id()
        item: dict[str, Any] = {
            "PK": run_pk(user_id, project_id),
            "SK": run_sk(rid),
            "GS2PK": run_gs2pk(user_id, project_id, data.workspace_id),
            "id": rid,
            "userId": user_id,
            "projectId": project_id,
            "workspaceId": data.workspace_id,
            "status": RunStatus.PENDING.value,
            "pipeline": data.pipeline,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        await self._put(item)
        return _item_to_model(item)

    async def get(self, user_id: str, project_id: str, run_id: str) -> Run | None:
        item = await self._get(run_pk(user_id, project_id), run_sk(run_id))
        return _item_to_model(item) if item else None

    async def update_status(
        self,
        user_id: str,
        project_id: str,
        run_id: str,
        status: RunStatus,
        output: str | None = None,
        error: str | None = None,
    ) -> Run | None:
        now = datetime.now(UTC)
        values: dict[str, Any] = {"status": status.value}

        if status == RunStatus.RUNNING:
            values["startedAt"] = now.isoformat()
        if status in (RunStatus.COMPLETED, RunStatus.FAILED):
            values["completedAt"] = now.isoformat()
        if output is not None:
            values["output"] = output
        if error is not None:
            values["error"] = error

        attrs = await self._update(run_pk(user_id, project_id), run_sk(run_id), values)
        return _item_to_model(attrs) if attrs else None

    async def list_by_project(
        self,
        user_id: str,
        project_id: str,
        workspace_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Run]:
        if workspace_id is not None:
            items = await self._query_gsi("gs2", "GS2PK", run_gs2pk(user_id, project_id, workspace_id))
        else:
            items = await self._query_by_pk(run_pk(user_id, project_id), sk_prefix="RUN#")

        runs = [_item_to_model(item) for item in items]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[offset : offset + limit]
