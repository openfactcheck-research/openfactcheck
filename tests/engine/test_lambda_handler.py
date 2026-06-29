"""Tests for the engine Lambda handler (in-process execution + env isolation)."""

import asyncio
import os
from collections.abc import Awaitable, Callable

from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from openfactcheck.engine import lambda_handler
from openfactcheck.engine.executor import ExecutionResult

EVENT = {"user_id": "u1", "pipeline": {"blocks": {"blocks": []}}}

PipelineRunner = Callable[[dict[str, object]], Awaitable[ExecutionResult]]


def _fake_run(captured: dict[str, str], result: ExecutionResult) -> PipelineRunner:
    """Build a fake execute_pipeline that snapshots os.environ at run time."""

    async def run(_pipeline: dict[str, object]) -> ExecutionResult:
        captured.clear()
        captured.update(os.environ)
        return result

    return run


def test_handler_success(mocker: MockerFixture) -> None:
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={})
    mocker.patch.object(lambda_handler, "execute_pipeline", _fake_run({}, ExecutionResult(success=True, output="Paris")))

    result = lambda_handler.handler(EVENT, None)

    assert result == {"success": True, "output": "Paris", "error": ""}


def test_handler_failure(mocker: MockerFixture) -> None:
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={})
    mocker.patch.object(
        lambda_handler,
        "execute_pipeline",
        _fake_run({}, ExecutionResult(success=False, output="", error="boom")),
    )

    result = lambda_handler.handler(EVENT, None)

    assert result["success"] is False
    assert result["error"] == "boom"


def test_handler_injects_secrets_during_run_and_restores_after(mocker: MockerFixture) -> None:
    captured: dict[str, str] = {}
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={"OPENAI_API_KEY": "sk-1"})
    mocker.patch.object(lambda_handler, "execute_pipeline", _fake_run(captured, ExecutionResult(success=True, output="")))

    lambda_handler.handler(EVENT, None)

    assert captured["OPENAI_API_KEY"] == "sk-1"  # present during the run
    assert "OPENAI_API_KEY" not in os.environ  # removed after the run


def test_handler_does_not_override_baseline_env(mocker: MockerFixture) -> None:
    captured: dict[str, str] = {}
    original_path = os.environ["PATH"]
    mocker.patch.object(
        lambda_handler,
        "resolve_user_secrets",
        return_value={"PATH": "evil", "OPENAI_API_KEY": "sk-1"},
    )
    mocker.patch.object(lambda_handler, "execute_pipeline", _fake_run(captured, ExecutionResult(success=True, output="")))

    lambda_handler.handler(EVENT, None)

    assert captured["PATH"] == original_path  # baseline var not shadowed by a user secret
    assert captured["OPENAI_API_KEY"] == "sk-1"


def test_handler_isolates_secrets_across_invocations(mocker: MockerFixture) -> None:
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={"OPENAI_API_KEY": "user-a-key"})
    mocker.patch.object(lambda_handler, "execute_pipeline", _fake_run({}, ExecutionResult(success=True, output="")))
    lambda_handler.handler(EVENT, None)  # user A runs with a key

    captured_b: dict[str, str] = {}
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={})  # user B has no secrets
    mocker.patch.object(lambda_handler, "execute_pipeline", _fake_run(captured_b, ExecutionResult(success=True, output="")))
    lambda_handler.handler(EVENT, None)  # user B runs next

    assert "OPENAI_API_KEY" not in captured_b  # user A's key is not visible to user B


def test_handler_timeout_returns_clean_error_and_restores_env(mocker: MockerFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(lambda_handler, "_RUN_TIMEOUT_SECONDS", 0.01)
    mocker.patch.object(lambda_handler, "resolve_user_secrets", return_value={"OPENAI_API_KEY": "sk-1"})

    async def slow(_pipeline: dict[str, object]) -> ExecutionResult:
        await asyncio.sleep(1)
        return ExecutionResult(success=True, output="")

    mocker.patch.object(lambda_handler, "execute_pipeline", slow)

    result = lambda_handler.handler(EVENT, None)

    assert result["success"] is False
    assert "timed out" in result["error"].lower()
    assert "OPENAI_API_KEY" not in os.environ  # env restored even on timeout
