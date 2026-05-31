from __future__ import annotations

import pytest

from app.services.perplexity_sonar_service import search_legal_sources_with_sonar
from app.services.provider_errors import ProviderError


def test_perplexity_service_parses_valid_json_and_search_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"legal_sources":[{"title":"Source","url":"https://www.consultant.ru/doc/1",'
                            '"source_type":"consultant_plus","relevance":"high","snippet":"Snippet"}],'
                            '"warnings":[]}'
                        )
                    }
                }
            ],
            "citations": ["https://www.consultant.ru/doc/1"],
            "search_results": [
                {
                    "title": "Source",
                    "url": "https://www.consultant.ru/doc/1",
                    "snippet": "Snippet",
                    "source": "web",
                    "date": "2025-01-01",
                    "last_updated": "2025-01-02",
                }
            ],
            "usage": {"total_tokens": 42},
        }

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    result = search_legal_sources_with_sonar(
        query="legal query",
        context={"document_id": "doc-1"},
        domains=["consultant.ru"],
        model="sonar-pro",
        api_key="token",
        base_url="https://api.perplexity.ai",
    )

    assert result.parsed_json is not None
    assert result.parsed_json["legal_sources"][0]["url"] == "https://www.consultant.ru/doc/1"
    assert len(result.search_results) == 1
    assert len(result.citations) == 1
    assert result.usage == {"total_tokens": 42}


def test_perplexity_service_invalid_json_keeps_search_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        return {
            "choices": [{"message": {"content": "not-json"}}],
            "search_results": [
                {
                    "title": "Fallback source",
                    "url": "https://www.garant.ru/doc/2",
                    "snippet": "Fallback snippet",
                }
            ],
            "citations": [],
        }

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    result = search_legal_sources_with_sonar(
        query="legal query",
        context={"document_id": "doc-2"},
        domains=["garant.ru"],
        model="sonar-pro",
        api_key="token",
        base_url="https://api.perplexity.ai",
    )

    assert result.parsed_json is None
    assert len(result.search_results) == 1
    assert result.search_results[0]["url"] == "https://www.garant.ru/doc/2"


def test_perplexity_service_citations_only_is_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        return {
            "choices": [{"message": {"content": "{}"}}],
            "citations": ["https://pravo.gov.ru/example"],
        }

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    result = search_legal_sources_with_sonar(
        query="legal query",
        context={"document_id": "doc-3"},
        domains=["pravo.gov.ru"],
        model="sonar-pro",
        api_key="token",
        base_url="https://api.perplexity.ai",
    )

    assert result.parsed_json == {}
    assert result.search_results == []
    assert result.citations == ["https://pravo.gov.ru/example"]


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "provider_auth_failed"),
        (429, "provider_rate_limited"),
        (503, "provider_unavailable"),
    ],
)
def test_perplexity_service_propagates_provider_error_codes(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_code: str,
) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        raise ProviderError(
            provider="perplexity",
            code=expected_code,
            message="failure",
            status_code=status_code,
            retryable=expected_code in {"provider_rate_limited", "provider_unavailable"},
        )

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    with pytest.raises(ProviderError) as exc_info:
        search_legal_sources_with_sonar(
            query="legal query",
            context={"document_id": "doc-4"},
            domains=["consultant.ru"],
            model="sonar-pro",
            api_key="token",
            base_url="https://api.perplexity.ai",
        )
    assert exc_info.value.code == expected_code
    assert exc_info.value.provider == "perplexity"


def test_perplexity_service_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        raise ProviderError(
            provider="perplexity",
            code="provider_timeout",
            message="timeout",
            retryable=True,
        )

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    with pytest.raises(ProviderError) as exc_info:
        search_legal_sources_with_sonar(
            query="legal query",
            context={"document_id": "doc-5"},
            domains=["consultant.ru"],
            model="sonar-pro",
            api_key="token",
            base_url="https://api.perplexity.ai",
        )
    assert exc_info.value.code == "provider_timeout"


def test_perplexity_service_bad_response_on_malformed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post_chat_completion_text(**_kwargs):
        return {"not_choices": []}

    monkeypatch.setattr(
        "app.services.perplexity_sonar_service.post_chat_completion_text",
        fake_post_chat_completion_text,
    )

    with pytest.raises(ProviderError) as exc_info:
        search_legal_sources_with_sonar(
            query="legal query",
            context={"document_id": "doc-6"},
            domains=["consultant.ru"],
            model="sonar-pro",
            api_key="token",
            base_url="https://api.perplexity.ai",
        )
    assert exc_info.value.code == "provider_bad_response"
