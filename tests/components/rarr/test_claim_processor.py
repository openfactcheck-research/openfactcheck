"""Tests for RARRClaimProcessor."""

import pytest

from openfactcheck.components import ClaimProcessor
from openfactcheck.components.rarr import RARRClaimProcessor
from openfactcheck.components.types import Claim, Input


def test_RARRClaimProcessor_satisfies_protocol() -> None:
    assert isinstance(RARRClaimProcessor(), ClaimProcessor)


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRClaimProcessor_returns_whole_input_as_one_claim() -> None:
    processor = RARRClaimProcessor()

    result = await processor(Input(content="The sky is blue. Water is wet."))

    assert result == [Claim(text="The sky is blue. Water is wet.")]
