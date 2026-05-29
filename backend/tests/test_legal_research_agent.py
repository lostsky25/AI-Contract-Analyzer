from app.agents.legal_research_agent import (
    build_search_queries,
    classify_source_type,
    parse_allowed_domains,
    url_matches_allowed_domains,
)


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
