"""RARR components.

A port of RARR (Gao et al., 2023), a research-and-revise approach to attribution
and factuality. The components mirror the paper's stages: take the input as one
passage, generate comprehensive verification questions, retrieve one piece of
evidence per question, then iteratively check the passage against each piece of
evidence (the agreement gate) and edit it to agree when it disagrees (the
editor). A separate selector picks the evidence that best covers the questions as
an attribution report.

The agreement gate and editor run a sequential loop in which the passage is
revised in place, so each check sees the latest version; the pipeline expresses
this as a graph cycle over the reviser (the gate-and-edit loop body), then an
aggregator consolidates the checks and the revised passage into a result. The
retriever, agreement gate, editor, evidence selector, reviser, and aggregator are
specific to RARR's shape and do not implement the shared component protocols.

The LLM components run on an injected chat client;
[`PROVENANCE`][PROVENANCE] records the recommended
default model along with the source paper, repository, pinned commit, and
license. Import from ``openfactcheck.components.rarr``.
"""

from typing import TYPE_CHECKING

from openfactcheck.components.provenance import Provenance
from openfactcheck.components.rarr.aggregator import RARRAggregator
from openfactcheck.components.rarr.agreement_gate import RARRAgreementGate, RARRAgreementGateModel
from openfactcheck.components.rarr.claim_processor import RARRClaimProcessor
from openfactcheck.components.rarr.editor import RARREditor, RARREditorModel
from openfactcheck.components.rarr.errors import RARRConfigError, RARRError
from openfactcheck.components.rarr.evidence_selector import RARREvidenceSelector
from openfactcheck.components.rarr.query_generator import RARRQueryGenerator, RARRQueryGeneratorModel
from openfactcheck.components.rarr.retriever import QuestionedSource, RARRRetriever
from openfactcheck.components.rarr.reviser import RARRResearch, RARRReviser

_CITATION = """\
@inproceedings{gao-etal-2023-rarr,
    title={RARR: Researching and Revising What Language Models Say, Using Language Models},
    author={Gao, Luyu and Dai, Zhuyun and Pasupat, Panupong and Chen, Anthony and
            Chaganty, Arun Tejasvi and Fan, Yicheng and Zhao, Vincent and Lao, Ni and
            Lee, Hongrae and Juan, Da-Cheng and Guu, Kelvin},
    booktitle={Proceedings of the 61st Annual Meeting of the Association for
               Computational Linguistics (Volume 1: Long Papers)},
    year={2023},
    url={https://aclanthology.org/2023.acl-long.910/},
}"""

PROVENANCE = Provenance(
    paper_title="RARR: Researching and Revising What Language Models Say, Using Language Models",
    paper_url="https://aclanthology.org/2023.acl-long.910/",
    citation=_CITATION,
    repository_url="https://github.com/anthonywchen/RARR",
    repository_commit="51a1a10fe5bada837a368f98cb55288ac5168c9e",
    license="N/A",
    default_model="gpt-4o-mini",
    paper_models=("text-davinci-003", "palm-540b"),
)
"""Provenance for the RARR components."""

# Components
__all__ = [
    "RARRAggregator",
    "RARRAgreementGate",
    "RARRClaimProcessor",
    "RARREditor",
    "RARREvidenceSelector",
    "RARRQueryGenerator",
    "RARRRetriever",
    "RARRReviser",
]

# Structured outputs (the value each LLM component's ``on_partial`` hook streams)
__all__ += [
    "RARRAgreementGateModel",
    "RARREditorModel",
    "RARRQueryGeneratorModel",
]

# Types
__all__ += [
    "QuestionedSource",
    "RARRResearch",
]

# Errors
__all__ += [
    "RARRConfigError",
    "RARRError",
]

# Provenance
__all__ += [
    "PROVENANCE",
]


if TYPE_CHECKING:
    from openfactcheck.components.protocols import ClaimProcessor, QueryGenerator

    # Type-only conformance: each RARR component that implements a shared category
    # protocol must satisfy it, so pyright fails the gate the moment one drifts.
    # The retriever, agreement gate, editor, selector, reviser, and aggregator are
    # RARR-specific and bind to no protocol. Absent at runtime.
    _processor: type[ClaimProcessor] = RARRClaimProcessor
    _generator: type[QueryGenerator] = RARRQueryGenerator
