"""Tests for the Factool provenance record."""

from openfactcheck.components import Provenance
from openfactcheck.components.factool import PROVENANCE


def test_factool_provenance_records_pinned_source() -> None:
    assert isinstance(PROVENANCE, Provenance)
    assert PROVENANCE.paper_url.endswith("2307.13528")
    assert PROVENANCE.repository_url == "https://github.com/GAIR-NLP/factool"
    assert len(PROVENANCE.repository_commit) == 40  # noqa: PLR2004 - a full git SHA-1.
    assert PROVENANCE.license == "Apache-2.0"
    assert PROVENANCE.default_model == "gpt-4o-mini"
    assert "@article{" in PROVENANCE.citation
    assert "2307.13528" in PROVENANCE.citation
