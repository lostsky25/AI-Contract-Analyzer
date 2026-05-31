from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _restore_settings():
    snapshot = {
        "bothub_api_key": settings.bothub_api_key,
        "bothub_api_base_url": settings.bothub_api_base_url,
        "legal_research_provider": settings.legal_research_provider,
        "openrouter_api_key": settings.openrouter_api_key,
    }
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


def test_legal_research_provider_bothub_is_supported() -> None:
    settings.legal_research_provider = "bothub_sonar"
    assert settings.get_legal_research_provider() == "bothub_sonar"


def test_legal_research_provider_openrouter_is_supported() -> None:
    settings.legal_research_provider = "openrouter_web_search"
    assert settings.get_legal_research_provider() == "openrouter_web_search"


def test_legal_research_provider_disabled_is_supported() -> None:
    settings.legal_research_provider = "disabled"
    assert settings.get_legal_research_provider() == "disabled"


def test_legal_research_provider_unknown_falls_back_to_bothub() -> None:
    settings.legal_research_provider = "unexpected"
    assert settings.get_legal_research_provider() == "bothub_sonar"


def test_legal_research_provider_perplexity_alias_is_not_active() -> None:
    settings.legal_research_provider = "perplexity_sonar"
    assert settings.get_legal_research_provider() == "bothub_sonar"


def test_bothub_legal_research_key_resolution_uses_shared_key() -> None:
    settings.legal_research_provider = "bothub_sonar"
    settings.bothub_api_key = "shared-token"
    assert settings.get_legal_research_api_key() == "shared-token"


def test_openrouter_legal_research_key_resolution_uses_openrouter_key() -> None:
    settings.legal_research_provider = "openrouter_web_search"
    settings.openrouter_api_key = "openrouter-token"
    assert settings.get_legal_research_api_key() == "openrouter-token"


def test_legal_research_model_reported_sources_flag_is_boolean() -> None:
    assert isinstance(settings.legal_research_allow_model_reported_sources, bool)


def test_legal_research_debug_flag_is_boolean() -> None:
    assert isinstance(settings.legal_research_debug, bool)
