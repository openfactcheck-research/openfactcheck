"""Tests for the graph error hierarchy."""

import pytest

from openfactcheck.graph import (
    GraphBuildError,
    GraphError,
    GraphRuntimeError,
    GraphValidationError,
)


@pytest.mark.parametrize(
    "error_type",
    [GraphBuildError, GraphValidationError, GraphRuntimeError],
)
def test_GraphError_subclasses(error_type: type[GraphError]) -> None:
    assert issubclass(error_type, GraphError)
    with pytest.raises(GraphError):
        raise error_type("boom")
