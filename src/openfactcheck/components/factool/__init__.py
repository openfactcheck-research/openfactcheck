"""Factool knowledge-QA components.

A port of the knowledge-based QA factuality pipeline from FacTool (Chern et al.,
2023). The components mirror the paper's stages: extract atomic claims, generate
skeptical search queries, retrieve web evidence, and verify each claim against
that evidence.

The LLM components run on an injected chat client;
[`PROVENANCE`][PROVENANCE] records the
recommended default model along with the source paper, repository, pinned
commit, and license. Import from ``openfactcheck.components.factool``.
"""

from collections.abc import Mapping
from typing import TYPE_CHECKING

from openfactcheck.components.factool.claim_processor import FactoolClaimProcessor, FactoolClaimProcessorModel
from openfactcheck.components.factool.query_generator import FactoolQueryGenerator, FactoolQueryGeneratorModel
from openfactcheck.components.factool.retriever import FactoolRetriever
from openfactcheck.components.factool.verifier import FactoolVerifier, FactoolVerifierModel
from openfactcheck.components.provenance import Provenance
from openfactcheck.components.registry import Component

_CITATION = """\
@article{chern2023factoolfactualitydetectiongenerative,
    title={FacTool: Factuality Detection in Generative AI -- A Tool Augmented
           Framework for Multi-Task and Multi-Domain Scenarios},
    author={I-Chun Chern and Steffi Chern and Shiqi Chen and Weizhe Yuan and
            Kehua Feng and Chunting Zhou and Junxian He and Graham Neubig and
            Pengfei Liu},
    year={2023},
    eprint={2307.13528},
    archivePrefix={arXiv},
    primaryClass={cs.CL},
    url={https://arxiv.org/abs/2307.13528},
}"""

PROVENANCE = Provenance(
    paper_title=(
        "FacTool: Factuality Detection in Generative AI - "
        "A Tool Augmented Framework for Multi-Task and Multi-Domain Scenarios"
    ),
    paper_url="https://arxiv.org/abs/2307.13528",
    citation=_CITATION,
    repository_url="https://github.com/GAIR-NLP/factool",
    repository_commit="3f3914bc090b644be044b7e0005113c135d8b20f",
    license="Apache-2.0",
    default_model="gpt-4o-mini",
    paper_models=("gpt-3.5-turbo-0301", "gpt-4-0314"),
)
"""Provenance for the Factool knowledge-QA components."""

# Components
__all__ = [
    "FactoolClaimProcessor",
    "FactoolQueryGenerator",
    "FactoolRetriever",
    "FactoolVerifier",
]

# Structured outputs (the value each component's ``on_partial`` hook streams)
__all__ += [
    "FactoolClaimProcessorModel",
    "FactoolQueryGeneratorModel",
    "FactoolVerifierModel",
]

# Provenance
__all__ += [
    "PROVENANCE",
]


if TYPE_CHECKING:
    from openfactcheck.components.protocols import (
        ClaimProcessor,
        QueryGenerator,
        Retriever,
        Verifier,
    )

    # Type-only conformance: each Factool component must satisfy its category protocol,
    # so pyright fails the gate the moment one drifts. Absent at runtime.
    _processor: type[ClaimProcessor] = FactoolClaimProcessor
    _generator: type[QueryGenerator] = FactoolQueryGenerator
    _retriever: type[Retriever] = FactoolRetriever
    _verifier: type[Verifier] = FactoolVerifier


COMPONENTS: Mapping[str, Component] = {
    "claim_processor": Component(
        factory=FactoolClaimProcessor, role="claim_processor", default_model=PROVENANCE.default_model
    ),
    "query_generator": Component(
        factory=FactoolQueryGenerator, role="query_generator", default_model=PROVENANCE.default_model
    ),
    "retriever": Component(factory=FactoolRetriever, role="retriever"),
    "verifier": Component(factory=FactoolVerifier, role="verifier", default_model=PROVENANCE.default_model),
}
"""The Factool components, discovered through the ``openfactcheck.components`` entry point."""
