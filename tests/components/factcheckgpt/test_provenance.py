"""Tests for the FactcheckGPT provenance record."""

from openfactcheck.components import Provenance
from openfactcheck.components.factcheckgpt import PROVENANCE


def test_factcheckgpt_provenance_records_pinned_source() -> None:
    assert isinstance(PROVENANCE, Provenance)
    assert PROVENANCE.paper_url.endswith("2024.findings-emnlp.830/")
    assert PROVENANCE.repository_url == "https://github.com/yuxiaw/Factcheck-GPT"
    assert len(PROVENANCE.repository_commit) == 40  # noqa: PLR2004 - a full git SHA-1.
    assert PROVENANCE.license == "Apache-2.0"
    assert PROVENANCE.default_model == "gpt-4o-mini"
    assert "@inproceedings{" in PROVENANCE.citation
    assert "2024.findings-emnlp.830" in PROVENANCE.citation
