"""Tests for the RARR provenance record."""

from openfactcheck.components import Provenance
from openfactcheck.components.rarr import PROVENANCE


def test_rarr_provenance_records_pinned_source() -> None:
    assert isinstance(PROVENANCE, Provenance)
    assert PROVENANCE.paper_url.endswith("2023.acl-long.910/")
    assert PROVENANCE.repository_url == "https://github.com/anthonywchen/RARR"
    assert len(PROVENANCE.repository_commit) == 40  # noqa: PLR2004 - a full git SHA-1.
    assert PROVENANCE.license == "N/A"
    assert PROVENANCE.default_model == "gpt-4o-mini"
    assert "@inproceedings{" in PROVENANCE.citation
    assert "2023.acl-long.910" in PROVENANCE.citation
