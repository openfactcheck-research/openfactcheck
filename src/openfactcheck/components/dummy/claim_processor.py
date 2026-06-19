"""Dummy claim processor."""

from dataclasses import dataclass

from openfactcheck.components.types import Claim, Input


@dataclass(frozen=True, slots=True)
class DummyClaimProcessor:
    """Claim processor that performs no extraction.

    Wraps the whole input as a single claim, or yields nothing when the input is
    blank.
    """

    async def __call__(self, text: Input) -> list[Claim]:
        """Wrap ``text`` as a single claim.

        Args:
            text: Input to turn into claims.

        Returns:
            One claim holding the full input content, or an empty list when the
            content is blank.
        """
        if not text.content.strip():
            return []
        return [Claim(text=text.content)]
