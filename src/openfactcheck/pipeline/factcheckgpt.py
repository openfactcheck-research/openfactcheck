"""The FactcheckGPT pipeline.

Pairs the [FactcheckGPT][openfactcheck.components.factcheckgpt] components with the fact-check graph,
built with revision, into a ready-to-run [`Pipeline`][openfactcheck.pipeline.Pipeline]. The LLM components
share an injected chat client; the retriever scrapes the web for evidence.
"""

from openfactcheck.chat import ChatClient
from openfactcheck.components.factcheckgpt import (
    FactcheckGPTAggregator,
    FactcheckGPTClaimProcessor,
    FactcheckGPTQueryGenerator,
    FactcheckGPTRetriever,
    FactcheckGPTReviser,
    FactcheckGPTVerifier,
)
from openfactcheck.integrations.google_scraper import GoogleScraperClient
from openfactcheck.pipeline.pipeline import Components, Pipeline, build_graph


def factcheckgpt(chat: ChatClient, scraper: GoogleScraperClient | None = None) -> Pipeline:
    """Build the FactcheckGPT fact-check pipeline.

    Wires the FactcheckGPT components onto the fact-check graph built with
    revision. The claim processor, query generator, verifier, and reviser run on
    ``chat``; the retriever runs on ``scraper``.

    Args:
        chat: Chat client backing the LLM components. Its model is the caller's
            choice; the paper's recommended default is recorded on the
            FactcheckGPT components' provenance.
        scraper: Web retrieval client for the retriever. Defaults to a
            [`GoogleScraperClient`][openfactcheck.integrations.google_scraper.GoogleScraperClient],
            which needs the ``factcheckgpt`` extra.

    Returns:
        A pipeline that runs the FactcheckGPT method end to end, including the
        final revision of the input.
    """
    scraper = scraper if scraper is not None else GoogleScraperClient()
    components = Components(
        claim_processor=FactcheckGPTClaimProcessor(client=chat),
        query_generator=FactcheckGPTQueryGenerator(client=chat),
        retriever=FactcheckGPTRetriever(scraper=scraper),
        verifier=FactcheckGPTVerifier(client=chat),
        aggregator=FactcheckGPTAggregator(),
        reviser=FactcheckGPTReviser(client=chat),
    )
    return Pipeline(build_graph(revise=True), components)
