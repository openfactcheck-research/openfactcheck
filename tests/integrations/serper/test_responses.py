"""Tests for Serper response parsing."""

from openfactcheck.integrations.serper import ScrapeResponse, SearchResponse

_SEARCH_PAYLOAD = {
    "searchParameters": {"q": "openai", "type": "search", "gl": "us", "hl": "en", "num": 10},
    "knowledgeGraph": {
        "title": "OpenAI",
        "type": "Company",
        "website": "https://openai.com",
        "description": "AI research lab",
        "attributes": {"Founded": "2015", "CEO": "Sam Altman"},
    },
    "answerBox": {
        "snippet": "OpenAI is an AI research lab.",
        "snippetHighlighted": ["AI research lab"],
        "title": "OpenAI",
        "link": "https://openai.com",
    },
    "organic": [
        {
            "title": "OpenAI",
            "link": "https://openai.com",
            "snippet": "Official site",
            "position": 1,
            "sitelinks": [{"title": "About", "link": "https://openai.com/about"}],
        },
        {"title": "OpenAI - Wikipedia", "link": "https://en.wikipedia.org/wiki/OpenAI", "position": 2},
    ],
    "peopleAlsoAsk": [{"question": "Who founded OpenAI?", "snippet": "Founded in 2015.", "link": "https://x"}],
    "relatedSearches": [{"query": "openai chatgpt"}],
    "topStories": [{"title": "A news item"}],
}


def test_SearchResponse_parses_camelcase_fields() -> None:
    response = SearchResponse.model_validate(_SEARCH_PAYLOAD)

    assert response.search_parameters is not None
    assert response.search_parameters.q == "openai"
    assert response.search_parameters.type == "search"
    assert response.organic[0].title == "OpenAI"
    assert response.organic[0].sitelinks[0].title == "About"
    assert response.organic[1].snippet is None
    assert response.knowledge_graph is not None
    assert response.knowledge_graph.attributes["CEO"] == "Sam Altman"
    assert response.answer_box is not None
    assert response.answer_box.snippet_highlighted == ["AI research lab"]
    assert response.people_also_ask[0].question == "Who founded OpenAI?"
    assert response.related_searches[0].query == "openai chatgpt"


def test_SearchResponse_preserves_unmodeled_fields() -> None:
    response = SearchResponse.model_validate(_SEARCH_PAYLOAD)

    # Unknown top-level keys are kept rather than rejected.
    assert response.model_extra is not None
    assert "topStories" in response.model_extra


def test_SearchResponse_defaults_for_empty_payload() -> None:
    response = SearchResponse.model_validate({})

    assert response.organic == []
    assert response.people_also_ask == []
    assert response.knowledge_graph is None
    assert response.answer_box is None


def test_ScrapeResponse_parses_fields() -> None:
    response = ScrapeResponse.model_validate(
        {"text": "page text", "markdown": "# page text", "metadata": {"title": "Page"}, "credits": 1}
    )

    assert response.text == "page text"
    assert response.markdown == "# page text"
    assert response.metadata["title"] == "Page"
    assert response.credits == 1
