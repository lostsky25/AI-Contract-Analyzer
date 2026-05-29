from app.agents.legal_research_agent import (
    LegalResearchAgent,
    LegalSourceItem,
    _normalize_sources,
    build_search_queries,
    classify_source_type,
    parse_allowed_domains,
    url_matches_allowed_domains,
)
from app.config import settings


def test_build_search_queries_returns_up_to_four() -> None:
    queries = build_search_queries(
        summary="Договор поставки",
        risks=[{"title": "Одностороннее изменение цены", "explanation": "..."}],
        key_terms=[{"title": "Срок оплаты", "value": "30 дней"}],
    )
    assert 2 <= len(queries) <= 4
    assert any("расторж" in query.lower() for query in queries)


def test_classify_source_type() -> None:
    assert classify_source_type("https://www.consultant.ru/document/1") == "consultant_plus"
    assert classify_source_type("https://base.garant.ru/123") == "garant"
    assert classify_source_type("https://pravo.gov.ru/proxy/") == "pravo_gov"


def test_url_matches_allowed_domains() -> None:
    allowed = parse_allowed_domains("consultant.ru,garant.ru,pravo.gov.ru")
    assert url_matches_allowed_domains("https://www.consultant.ru/doc", allowed)
    assert not url_matches_allowed_domains("https://example.com/doc", allowed)


def test_normalize_sources_filters_disallowed_domains() -> None:
    allowed = parse_allowed_domains("consultant.ru,garant.ru,pravo.gov.ru")
    sources = _normalize_sources(
        [
            LegalSourceItem(
                title="Allowed",
                url="https://www.consultant.ru/doc/1",
                snippet="snippet",
                source_type="consultant_plus",
                relevance="high",
            ),
            LegalSourceItem(
                title="Blocked",
                url="https://example.com/doc",
                snippet="snippet",
                source_type="other_public_source",
                relevance="low",
            ),
        ],
        allowed,
    )
    assert len(sources) == 1
    assert sources[0]["source_type"] == "consultant_plus"


def test_normalize_sources_deduplicates_normalized_urls() -> None:
    allowed = parse_allowed_domains("consultant.ru,garant.ru,pravo.gov.ru")
    sources = _normalize_sources(
        [
            LegalSourceItem(
                title="Doc",
                url="https://www.consultant.ru/doc/1/",
                snippet="snippet 1",
                source_type="consultant_plus",
                relevance="high",
            ),
            LegalSourceItem(
                title="Doc duplicate",
                url="https://www.consultant.ru/doc/1#toc",
                snippet="snippet 2",
                source_type="consultant_plus",
                relevance="medium",
            ),
        ],
        allowed,
    )
    assert len(sources) == 1
    assert sources[0]["url"] == "https://www.consultant.ru/doc/1"


def test_legal_research_without_api_key_returns_empty_sources(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "legal_web_search_enabled", True)

    result = LegalResearchAgent().run(
        document_id="doc-legal-1",
        risks=[{"title": "Penalty", "explanation": "High penalty rate."}],
        key_terms=[{"title": "Payment", "value": "30 days"}],
        summary="Supply contract",
    )

    assert result["legal_sources"] == []
    assert result["warnings"]
    assert any("unavailable" in warning.lower() for warning in result["warnings"])
