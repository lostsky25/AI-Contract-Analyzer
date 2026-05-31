from __future__ import annotations

import httpx
import pytest

from app.services.llm_provider_service import post_chat_completion_text
from app.services.provider_errors import ProviderError


class _DummyResponse:
    def __init__(self, status_code: int, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _patch_client_with_response(monkeypatch: pytest.MonkeyPatch, response: _DummyResponse) -> None:
    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, tb):
            return False

        def post(self, _url: str, *, headers: dict, json: dict):
            return response

    monkeypatch.setattr("app.services.llm_provider_service.httpx.Client", _Client)


def _patch_client_with_exception(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, tb):
            return False

        def post(self, _url: str, *, headers: dict, json: dict):
            raise exc

    monkeypatch.setattr("app.services.llm_provider_service.httpx.Client", _Client)


def test_bothub_200_response_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            status_code=200,
            payload={"choices": [{"message": {"content": "ok"}}]},
        ),
    )
    payload = post_chat_completion_text(
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "ping"}],
    )
    assert payload["choices"][0]["message"]["content"] == "ok"


def test_bothub_401_maps_to_provider_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=401, payload={"error": {"message": "unauthorized"}}),
    )
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_auth_failed"
    assert exc_info.value.provider == "bothub"


def test_bothub_429_maps_to_provider_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=429, payload={"error": {"message": "rate limited"}}),
    )
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_rate_limited"
    assert exc_info.value.retryable is True


def test_bothub_404_maps_to_provider_model_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=404, payload={"error": {"message": "model not found"}}),
    )
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
            model="missing-model",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_model_not_found"


def test_bothub_timeout_maps_to_provider_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_exception(monkeypatch, httpx.TimeoutException("timeout"))
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_timeout"
    assert exc_info.value.retryable is True


def test_bothub_malformed_response_maps_to_provider_bad_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_client_with_response(monkeypatch, _DummyResponse(status_code=200, payload=[]))
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_bad_response"


def test_perplexity_403_maps_to_provider_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=403, payload={"error": {"message": "forbidden"}}),
    )
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="perplexity",
            base_url="https://api.perplexity.ai",
            api_key="token",
            model="sonar-pro",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_auth_failed"
    assert exc_info.value.provider == "perplexity"


def test_perplexity_503_maps_to_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=503, payload={"error": {"message": "server error"}}),
    )
    with pytest.raises(ProviderError) as exc_info:
        post_chat_completion_text(
            provider="perplexity",
            base_url="https://api.perplexity.ai",
            api_key="token",
            model="sonar-pro",
            messages=[{"role": "user", "content": "ping"}],
        )
    assert exc_info.value.code == "provider_unavailable"
    assert exc_info.value.retryable is True
