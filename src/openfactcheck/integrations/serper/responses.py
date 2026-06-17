"""Typed responses from the Serper.dev API.

Field names are snake_case and aliased to Serper's camelCase JSON keys. Every
model tolerates unmodeled fields (``extra="allow"``), so new keys the service
adds are preserved on the instance rather than rejected.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_RESPONSE_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    extra="allow",
    frozen=True,
    use_attribute_docstrings=True,
)
"""Shared response config: snake_case fields aliased to camelCase, tolerant of unmodeled keys."""


class SearchParameters(BaseModel):
    """The search parameters echoed back by the service."""

    model_config = _RESPONSE_CONFIG

    q: str
    """The query that was searched."""

    type: str | None = None
    """The search type, such as ``search``."""

    gl: str | None = None
    """Country code applied to the search."""

    hl: str | None = None
    """Language code applied to the search."""

    location: str | None = None
    """Location applied to the search."""

    num: int | None = None
    """Number of results requested."""

    page: int | None = None
    """Result page number."""

    autocorrect: bool | None = None
    """Whether the query spelling was autocorrected."""


class Sitelink(BaseModel):
    """A secondary link shown beneath an organic result."""

    model_config = _RESPONSE_CONFIG

    title: str
    """The sitelink's display title."""

    link: str
    """The sitelink's URL."""


class OrganicResult(BaseModel):
    """A single organic (non-paid) search result."""

    model_config = _RESPONSE_CONFIG

    title: str
    """The result's title."""

    link: str
    """The result's URL."""

    snippet: str | None = None
    """A short extract from the page."""

    position: int | None = None
    """The result's rank on the page, starting at 1."""

    date: str | None = None
    """The page's date, when the service reports one."""

    sitelinks: list[Sitelink] = Field(default_factory=list[Sitelink])
    """Secondary links shown beneath the result."""

    attributes: dict[str, str] = Field(default_factory=dict[str, str])
    """Extra key-value details shown with the result."""


class KnowledgeGraph(BaseModel):
    """The structured entity panel shown alongside results."""

    model_config = _RESPONSE_CONFIG

    title: str | None = None
    """The entity's name."""

    type: str | None = None
    """The entity's category, such as ``Company``."""

    website: str | None = None
    """The entity's official website."""

    description: str | None = None
    """A short description of the entity."""

    attributes: dict[str, str] = Field(default_factory=dict[str, str])
    """Key facts about the entity, such as its founder or founding date."""


class AnswerBox(BaseModel):
    """A direct answer or featured snippet for the query."""

    model_config = _RESPONSE_CONFIG

    answer: str | None = None
    """The direct answer, when the service extracts one."""

    snippet: str | None = None
    """The featured snippet text."""

    snippet_highlighted: list[str] | None = None
    """Highlighted phrases within the snippet."""

    title: str | None = None
    """Title of the source page."""

    link: str | None = None
    """URL of the source page."""


class PeopleAlsoAsk(BaseModel):
    """A related question shown in the "People also ask" panel."""

    model_config = _RESPONSE_CONFIG

    question: str
    """The related question."""

    snippet: str | None = None
    """A short answer extract."""

    title: str | None = None
    """Title of the source page."""

    link: str | None = None
    """URL of the source page."""


class RelatedSearch(BaseModel):
    """A related query suggestion."""

    model_config = _RESPONSE_CONFIG

    query: str
    """The suggested query."""


class SearchResponse(BaseModel):
    """A response from the Serper.dev ``/search`` endpoint."""

    model_config = _RESPONSE_CONFIG

    search_parameters: SearchParameters | None = None
    """The search parameters echoed by the service."""

    organic: list[OrganicResult] = Field(default_factory=list[OrganicResult])
    """The organic search results, in rank order."""

    knowledge_graph: KnowledgeGraph | None = None
    """The entity panel, when one is shown for the query."""

    answer_box: AnswerBox | None = None
    """The direct answer or featured snippet, when present."""

    people_also_ask: list[PeopleAlsoAsk] = Field(default_factory=list[PeopleAlsoAsk])
    """Related questions shown for the query."""

    related_searches: list[RelatedSearch] = Field(default_factory=list[RelatedSearch])
    """Related query suggestions."""


class ScrapeResponse(BaseModel):
    """A response from the Serper.dev webpage scrape endpoint."""

    model_config = _RESPONSE_CONFIG

    text: str | None = None
    """The page's extracted plain text."""

    markdown: str | None = None
    """The page rendered as Markdown, when requested."""

    metadata: dict[str, str] = Field(default_factory=dict[str, str])
    """Metadata extracted from the page head."""

    jsonld: dict[str, object] | None = None
    """JSON-LD structured data found on the page, when present."""

    credits: int | None = None
    """API credits the scrape consumed."""
