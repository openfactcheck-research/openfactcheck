"""Tests for OpenFactCheckConfig — layered settings resolution."""

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from openfactcheck.config import OpenFactCheckConfig


@pytest.fixture(autouse=True)
def isolated_config_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate each test in a clean cwd with no conflicting env vars."""
    for key in list(os.environ):
        if key.startswith("OPENFACTCHECK_") or key == "SERPER_API_KEY":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_OpenFactCheckConfig_defaults() -> None:
    """Uses field defaults when no source provides a value."""
    config = OpenFactCheckConfig()

    assert config.model == "gpt-4o"
    assert config.verbosity == "warning"
    assert config.prompts_dir is None
    assert config.serper_api_key.get_secret_value() == ""


@pytest.mark.parametrize(
    ("disabled_sources", "expected_model"),
    [
        pytest.param(set[str](), "from-init", id="all-sources-init-wins"),
        pytest.param({"init"}, "from-env", id="no-init-env-wins"),
        pytest.param({"init", "env"}, "from-dotenv", id="no-env-dotenv-wins"),
        pytest.param({"init", "env", "dotenv"}, "from-json", id="no-dotenv-json-wins"),
        pytest.param({"init", "env", "dotenv", "json"}, "from-yaml", id="no-json-yaml-wins"),
        pytest.param({"init", "env", "dotenv", "json", "yaml"}, "gpt-4o", id="no-sources-default-wins"),
    ],
)
def test_OpenFactCheckConfig_resolution_order(
    isolated_config_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    disabled_sources: set[str],
    expected_model: str,
) -> None:
    """Full resolution chain: init > env > .env > json > yaml > default.

    Each parameter activates the full stack then disables the top N sources,
    asserting that the next-highest remaining source wins — proving the
    ordering end-to-end rather than pairwise.
    """
    if "yaml" not in disabled_sources:
        (isolated_config_env / "openfactcheck.yaml").write_text("model: from-yaml\n")
    if "json" not in disabled_sources:
        (isolated_config_env / "openfactcheck.json").write_text(json.dumps({"model": "from-json"}))
    if "dotenv" not in disabled_sources:
        (isolated_config_env / ".env").write_text("OPENFACTCHECK_MODEL=from-dotenv\n")
    if "env" not in disabled_sources:
        monkeypatch.setenv("OPENFACTCHECK_MODEL", "from-env")

    config = OpenFactCheckConfig(model="from-init") if "init" not in disabled_sources else OpenFactCheckConfig()

    assert config.model == expected_model


def test_OpenFactCheckConfig_serper_api_key_from_unprefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """SERPER_API_KEY env var is read without the OPENFACTCHECK_ prefix."""
    monkeypatch.setenv("SERPER_API_KEY", "secret-key-123")

    config = OpenFactCheckConfig()

    assert config.serper_api_key.get_secret_value() == "secret-key-123"


def test_OpenFactCheckConfig_serper_api_key_from_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENFACTCHECK_SERPER_API_KEY env var is also accepted via alias."""
    monkeypatch.setenv("OPENFACTCHECK_SERPER_API_KEY", "prefixed-key")

    config = OpenFactCheckConfig()

    assert config.serper_api_key.get_secret_value() == "prefixed-key"


def test_OpenFactCheckConfig_verbosity_rejects_invalid() -> None:
    """Verbosity validation rejects values outside the allowed literal set."""
    with pytest.raises(ValidationError):
        OpenFactCheckConfig(verbosity="trace")  # type: ignore[arg-type]
