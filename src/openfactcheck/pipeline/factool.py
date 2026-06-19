"""The Factool knowledge-QA pipeline.

Pairs the [Factool][openfactcheck.components.factool] components with the default fact-check graph into a
ready-to-run [`Pipeline`][openfactcheck.pipeline.Pipeline]. The LLM components share an injected chat
client; the retriever uses a web-search client.
"""

from openfactcheck.chat import ChatClient
from openfactcheck.components.factool import (
    FactoolAggregator,
    FactoolClaimProcessor,
    FactoolQueryGenerator,
    FactoolRetriever,
    FactoolVerifier,
)
from openfactcheck.integrations.serper import SerperClient
from openfactcheck.pipeline.pipeline import Components, Pipeline, build_graph


def factool(chat: ChatClient, serper: SerperClient | None = None) -> Pipeline:
    """Build the Factool knowledge-QA fact-check pipeline.

    Wires the Factool components onto the default fact-check graph. The claim
    processor, query generator, and verifier run on ``chat``; the retriever runs
    on ``serper``.

    Args:
        chat: Chat client backing the LLM components. Its model is the caller's
            choice; the paper's recommended default is recorded on the Factool
            components' provenance.
        serper: Web-search client for the retriever. Defaults to a
            [`SerperClient`][openfactcheck.integrations.serper.SerperClient] that
            reads its key from the environment.

    Returns:
        A pipeline that runs the Factool method end to end.
    """
    serper = serper if serper is not None else SerperClient()
    components = Components(
        claim_processor=FactoolClaimProcessor(client=chat),
        query_generator=FactoolQueryGenerator(client=chat),
        retriever=FactoolRetriever(serper=serper),
        verifier=FactoolVerifier(client=chat),
        aggregator=FactoolAggregator(),
    )
    return Pipeline(build_graph(), components)
