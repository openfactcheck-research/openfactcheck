"""Tests for RuntimeSpec."""

from openfactcheck.config import RuntimeSpec


def test_RuntimeSpec_to_runtime_config_inherits_defaults() -> None:
    """Unset fields take the chat runtime defaults."""
    runtime = RuntimeSpec(timeout=15.0).to_runtime_config()

    assert runtime.timeout == 15.0
    assert runtime.max_retries == 2


def test_RuntimeSpec_merged_over() -> None:
    """A spec's set fields override the base; unset fields fall through."""
    merged = RuntimeSpec(timeout=5.0).merged_over(RuntimeSpec(timeout=30.0, max_retries=4))

    assert merged.timeout == 5.0
    assert merged.max_retries == 4
