from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _restore_settings():
    snapshot = {
        "llm_provider": settings.llm_provider,
        "llm_api_key": settings.llm_api_key,
        "llm_api_base_url": settings.llm_api_base_url,
        "vision_provider": settings.vision_provider,
        "vision_api_key": settings.vision_api_key,
        "vision_api_base_url": settings.vision_api_base_url,
        "bothub_api_key": settings.bothub_api_key,
        "bothub_api_base_url": settings.bothub_api_base_url,
        "openrouter_api_key": settings.openrouter_api_key,
        "openrouter_base_url": settings.openrouter_base_url,
    }
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


def test_text_bothub_uses_shared_key() -> None:
    settings.llm_provider = "bothub"
    settings.bothub_api_key = "shared-token"
    assert settings.get_text_llm_api_key() == "shared-token"


def test_text_openrouter_uses_openrouter_key() -> None:
    settings.llm_provider = "openrouter"
    settings.openrouter_api_key = "openrouter-token"
    settings.bothub_api_key = "shared-token"
    assert settings.get_text_llm_api_key() == "openrouter-token"


def test_vision_bothub_uses_shared_key() -> None:
    settings.vision_provider = "bothub"
    settings.bothub_api_key = "shared-token"
    assert settings.get_vision_api_key() == "shared-token"


def test_vision_openrouter_uses_openrouter_key() -> None:
    settings.vision_provider = "openrouter"
    settings.openrouter_api_key = "openrouter-token"
    settings.bothub_api_key = "shared-token"
    assert settings.get_vision_api_key() == "openrouter-token"
