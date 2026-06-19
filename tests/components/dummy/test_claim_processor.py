"""Tests for DummyClaimProcessor."""

import pytest

from openfactcheck.components import ClaimProcessor
from openfactcheck.components.dummy import DummyClaimProcessor
from openfactcheck.components.types import Claim, Input


def test_DummyClaimProcessor_satisfies_protocol() -> None:
    assert isinstance(DummyClaimProcessor(), ClaimProcessor)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyClaimProcessor_wraps_input_as_single_claim() -> None:
    processor = DummyClaimProcessor()

    result = await processor(Input(content="The sky is blue."))

    assert result == [Claim(text="The sky is blue.")]


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyClaimProcessor_blank_input_yields_no_claims() -> None:
    processor = DummyClaimProcessor()

    result = await processor(Input(content="   "))

    assert result == []
