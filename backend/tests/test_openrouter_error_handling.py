from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.db_models import Document
from app.services.openrouter_service import ProviderError, post_chat_completion


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def _patch_httpx_client_with_response(
    monkeypatch: pytest.MonkeyPatch,
    response: _DummyResponse,
) -> None:
    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, _url: str, *, headers: dict, json: dict) -> _DummyResponse:
            return response

    monkeypatch.setattr("app.services.openrouter_service.httpx.Client", _Client)


def _patch_httpx_client_with_exception(
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
) -> None:
    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, exc_type, exc_value, tb) -> bool:
            return False

        def post(self, _url: str, *, headers: dict, json: dict) -> _DummyResponse:
            raise exc

    monkeypatch.setattr("app.services.openrouter_service.httpx.Client", _Client)


def test_openrouter_missing_key_maps_to_structured_code() -> None:
    previous = settings.openrouter_api_key
    settings.openrouter_api_key = ""
    try:
        with pytest.raises(ProviderError) as exc_info:
            post_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "ping"}],
            )
    finally:
        settings.openrouter_api_key = previous

    assert exc_info.value.code == "openrouter_missing_key"
    assert exc_info.value.provider == "openrouter"
    assert exc_info.value.retryable is False


def test_openrouter_429_maps_to_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = settings.openrouter_api_key
    settings.openrouter_api_key = "present"
    _patch_httpx_client_with_response(
        monkeypatch,
        _DummyResponse(
            status_code=429,
            payload={"error": {"message": "Rate limit exceeded"}},
        ),
    )
    try:
        with pytest.raises(ProviderError) as exc_info:
            post_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "ping"}],
            )
    finally:
        settings.openrouter_api_key = previous

    assert exc_info.value.code == "openrouter_rate_limited"
    assert exc_info.value.status_code == 429
    assert exc_info.value.retryable is True


def test_openrouter_404_no_endpoints_maps_to_model_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = settings.openrouter_api_key
    settings.openrouter_api_key = "present"
    _patch_httpx_client_with_response(
        monkeypatch,
        _DummyResponse(
            status_code=404,
            payload={"error": {"message": "No endpoints found for test-model"}},
        ),
    )
    try:
        with pytest.raises(ProviderError) as exc_info:
            post_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "ping"}],
            )
    finally:
        settings.openrouter_api_key = previous

    assert exc_info.value.code == "openrouter_model_not_found"
    assert exc_info.value.retryable is False


def test_openrouter_timeout_maps_to_timeout_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = settings.openrouter_api_key
    settings.openrouter_api_key = "present"
    _patch_httpx_client_with_exception(
        monkeypatch,
        httpx.TimeoutException("timeout"),
    )
    try:
        with pytest.raises(ProviderError) as exc_info:
            post_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "ping"}],
            )
    finally:
        settings.openrouter_api_key = previous

    assert exc_info.value.code == "openrouter_timeout"
    assert exc_info.value.retryable is True


@pytest.fixture
def route_document(tmp_path: Path) -> Document:
    path = tmp_path / "contract.docx"
    path.write_text("test", encoding="utf-8")
    return Document(
        id="provider-doc-1",
        user_id="test-user-id",
        filename="contract.docx",
        file_path=str(path),
        status="uploaded",
    )


def test_orchestrate_route_returns_structured_provider_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_document: Document,
) -> None:
    def fake_get_document(_db, document_id: str, user_id: str | None = None):
        if document_id == route_document.id and user_id == "test-user-id":
            return route_document
        return None

    def fake_run(**_kwargs):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_rate_limited",
            message="OpenRouter rate limit exceeded.",
            status_code=429,
            retryable=True,
        )

    monkeypatch.setattr("app.api.routes.get_document", fake_get_document)
    monkeypatch.setattr("app.api.routes.orchestrator.run", fake_run)

    response = client.post(
        "/api/orchestrate",
        json={"document_id": route_document.id, "legal_web_search_enabled": True},
    )
    assert response.status_code == 429
    payload = response.json()
    assert payload == {
        "detail": "OpenRouter rate limit exceeded.",
        "code": "openrouter_rate_limited",
        "provider": "openrouter",
        "retryable": True,
    }
