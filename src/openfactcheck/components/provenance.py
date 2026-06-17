"""Provenance metadata shared across ported components.

A paper port records where its components come from and what they are based on.
The concrete value lives in the port's own package; this module defines the
shared shape so every port reports the same fields, which a registry or docs
guide can surface uniformly.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a ported component comes from and what it is based on."""

    paper_title: str
    """Title of the source paper."""

    paper_url: str
    """URL of the source paper."""

    citation: str
    """BibTeX entry for the source paper, so users can cite the original work."""

    repository_url: str
    """URL of the authors' reference implementation."""

    repository_commit: str
    """Commit of the reference implementation this port was read against."""

    license: str
    """License of the reference implementation."""

    default_model: str
    """Recommended default model for the components, close to the paper's setup."""

    paper_models: tuple[str, ...]
    """Exact model snapshots reported in the paper's experiments."""
