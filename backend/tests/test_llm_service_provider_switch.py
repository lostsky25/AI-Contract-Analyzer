from __future__ import annotations

import pytest

from app.config import settings
from app.services.llm_service import ask_llm_text
from app.services.provider_errors import ProviderError


@pytest.fixture(autouse=True)
def _restore_llm_settings():
    snapshot = {
        "llm_provider": settings.llm_provider,
        "bothub_api_key": settings.bothub_api_key,
        "bothub_api_base_url": settings.bothub_api_base_url,
        "llm_api_base_url": settings.llm_api_base_url,
        "llm_api_key": settings.llm_api_key,
        "llm_model_risk": settings.llm_model_risk,
        "llm_model_key_terms": settings.llm_model_key_terms,
        "llm_model_qa": settings.llm_model_qa,
        "llm_model_fallback": settings.llm_model_fallback,
        "openrouter_api_key": settings.openrouter_api_key,
        "openrouter_model_risk": settings.openrouter_model_risk,
        "openrouter_model_key_terms": settings.openrouter_model_key_terms,
        "openrouter_model_qa": settings.openrouter_model_qa,
        "openrouter_model_fallback": settings.openrouter_model_fallback,
    }
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


def test_settings_model_resolution_openrouter_mode() -> None:
    settings.llm_provider = "openrouter"
    settings.openrouter_model_risk = "legacy-risk"
    assert settings.get_text_llm_model("risk") == "legacy-risk"


def test_settings_model_resolution_bothub_mode() -> None:
    settings.llm_provider = "bothub"
    settings.llm_model_risk = "bothub-risk"
    assert settings.get_text_llm_model("risk") == "bothub-risk"


def test_bothub_missing_key_raises_provider_missing_key() -> None:
    settings.llm_provider = "bothub"
    settings.bothub_api_base_url = "https://openai.bothub.chat/v1"
    settings.bothub_api_key = ""

    with pytest.raises(ProviderError) as exc_info:
        ask_llm_text("system", "user", model="gpt-5-mini")

    assert exc_info.value.code == "provider_missing_key"
    assert exc_info.value.provider == "bothub"


def test_bothub_fallback_uses_llm_model_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    settings.llm_provider = "bothub"
    settings.bothub_api_base_url = "https://openai.bothub.chat/v1"
    settings.bothub_api_key = "token"
    settings.llm_model_fallback = "bothub-fallback"

    def fake_post_chat_completion_text(*, model: str, **_kwargs):
        calls.append(model)
        if len(calls) == 1:
            raise ProviderError(
                provider="bothub",
                code="provider_unavailable",
                message="temporary outage",
                retryable=True,
            )
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.services.llm_service.post_chat_completion_text", fake_post_chat_completion_text)

    result = ask_llm_text("system", "user", model="bothub-primary")
    assert result == "ok"
    assert calls == ["bothub-primary", "bothub-fallback"]


def test_openrouter_fallback_uses_legacy_model_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    settings.llm_provider = "openrouter"
    settings.openrouter_api_key = "token"
    settings.openrouter_model_fallback = "legacy-fallback"

    def fake_post_chat_completion_text(*, model: str, **_kwargs):
        calls.append(model)
        if len(calls) == 1:
            raise ProviderError(
                provider="openrouter",
                code="provider_unavailable",
                message="temporary outage",
                retryable=True,
                legacy_code="openrouter_unavailable",
            )
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.services.llm_service.post_chat_completion_text", fake_post_chat_completion_text)

    result = ask_llm_text("system", "user", model="legacy-primary")
    assert result == "ok"
    assert calls == ["legacy-primary", "legacy-fallback"]


def test_bothub_uses_shared_key_when_llm_override_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.llm_provider = "bothub"
    settings.bothub_api_base_url = "https://openai.bothub.chat/v1"
    settings.bothub_api_key = "shared-token"

    captured: dict[str, str] = {}

    def fake_post_chat_completion_text(*, api_key: str, base_url: str, **_kwargs):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.services.llm_service.post_chat_completion_text", fake_post_chat_completion_text)

    result = ask_llm_text("system", "user", model="gpt-5-mini")
    assert result == "ok"
    assert captured["api_key"] == "shared-token"
    assert captured["base_url"] == "https://openai.bothub.chat/v1"
