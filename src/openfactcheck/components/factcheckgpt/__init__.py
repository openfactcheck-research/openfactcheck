"""FactcheckGPT components.

A port of the FactcheckGPT pipeline from Wang et al. (2024). The components
mirror the paper's stages: decompose the response into atomic checkworthy
claims, generate search queries, retrieve web evidence, verify each claim
against that evidence (with a correction when it is wrong), aggregate to a
response-level judgment, and revise the response to fix its errors.

The LLM components run on an injected chat client;
[`PROVENANCE`][openfactcheck.components.factcheckgpt.PROVENANCE] records the
recommended default model along with the source paper, repository, pinned
commit, and license. Import from ``openfactcheck.components.factcheckgpt``.
"""

from typing import TYPE_CHECKING

from openfactcheck.components.factcheckgpt.aggregator import FactcheckGPTAggregator
from openfactcheck.components.factcheckgpt.claim_processor import ClaimExtraction, FactcheckGPTClaimProcessor
from openfactcheck.components.factcheckgpt.query_generator import FactcheckGPTQueryGenerator, GeneratedQueries
from openfactcheck.components.factcheckgpt.retriever import FactcheckGPTRetriever
from openfactcheck.components.factcheckgpt.reviser import FactcheckGPTReviser, Revision
from openfactcheck.components.factcheckgpt.verifier import FactcheckGPTVerifier, Verification
from openfactcheck.components.provenance import Provenance

_CITATION = """\
@inproceedings{wang-etal-2024-factcheck-bench,
    title={Factcheck-Bench: Fine-Grained Evaluation Benchmark for Automatic Fact-Checkers},
    author={Wang, Yuxia and Reddy, Revanth Gangi and Mujahid, Zain Muhammad and
            Arora, Arnav and Rubashevskii, Aleksandr and Geng, Jiahui and
            Mohammed Afzal, Osama and Pan, Liangming and Borenstein, Nadav and
            Pillai, Aditya and Augenstein, Isabelle and Gurevych, Iryna and
            Nakov, Preslav},
    booktitle={Findings of the Association for Computational Linguistics: EMNLP 2024},
    year={2024},
    url={https://aclanthology.org/2024.findings-emnlp.830/},
}"""

PROVENANCE = Provenance(
    paper_title="Factcheck-Bench: Fine-Grained Evaluation Benchmark for Automatic Fact-Checkers",
    paper_url="https://aclanthology.org/2024.findings-emnlp.830/",
    citation=_CITATION,
    repository_url="https://github.com/yuxiaw/Factcheck-GPT",
    repository_commit="a9e6a04a953ad880806529c504a679dd1ad06528",
    license="Apache-2.0",
    default_model="gpt-4o-mini",
    paper_models=("gpt-3.5-turbo-0613",),
)
"""Provenance for the FactcheckGPT components."""

# Components
__all__ = [
    "FactcheckGPTAggregator",
    "FactcheckGPTClaimProcessor",
    "FactcheckGPTQueryGenerator",
    "FactcheckGPTRetriever",
    "FactcheckGPTReviser",
    "FactcheckGPTVerifier",
]

# Structured outputs (the value each component's ``on_partial`` hook streams)
__all__ += [
    "ClaimExtraction",
    "GeneratedQueries",
    "Revision",
    "Verification",
]

# Provenance
__all__ += [
    "PROVENANCE",
]


if TYPE_CHECKING:
    from openfactcheck.components.protocols import (
        Aggregator,
        ClaimProcessor,
        QueryGenerator,
        Retriever,
        Reviser,
        Verifier,
    )

    # Type-only conformance: each FactcheckGPT component must satisfy its category protocol,
    # so pyright fails the gate the moment one drifts. Absent at runtime.
    _processor: type[ClaimProcessor] = FactcheckGPTClaimProcessor
    _generator: type[QueryGenerator] = FactcheckGPTQueryGenerator
    _retriever: type[Retriever] = FactcheckGPTRetriever
    _verifier: type[Verifier] = FactcheckGPTVerifier
    _aggregator: type[Aggregator] = FactcheckGPTAggregator
    _reviser: type[Reviser] = FactcheckGPTReviser
