from __future__ import annotations

import pytest

from app.config import settings
from app.services.text_extractor import _resolve_vlm_configuration


@pytest.fixture(autouse=True)
def _restore_settings():
    snapshot = {
        "ocr_provider": settings.ocr_provider,
        "ocr_use_vlm": settings.ocr_use_vlm,
        "vision_provider": settings.vision_provider,
        "bothub_api_key": settings.bothub_api_key,
        "bothub_api_base_url": settings.bothub_api_base_url,
        "vision_api_base_url": settings.vision_api_base_url,
        "vision_api_key": settings.vision_api_key,
        "vision_model_ocr": settings.vision_model_ocr,
        "openrouter_api_key": settings.openrouter_api_key,
        "openrouter_model_ocr_vlm": settings.openrouter_model_ocr_vlm,
        "openrouter_ocr_model": settings.openrouter_ocr_model,
    }
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


def test_vision_provider_bothub_uses_shared_settings() -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.vision_provider = "bothub"
    settings.bothub_api_base_url = "https://openai.bothub.chat/v1"
    settings.bothub_api_key = "token"
    settings.vision_model_ocr = "gpt-4o"

    enabled, cfg, warning, _warnings = _resolve_vlm_configuration()
    assert enabled is True
    assert warning is None
    assert cfg["provider"] == "bothub"
    assert cfg["base_url"] == "https://openai.bothub.chat/v1"
    assert cfg["api_key"] == "token"
    assert cfg["model"] == "gpt-4o"


def test_vision_provider_bothub_uses_shared_key_when_override_missing() -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.vision_provider = "bothub"
    settings.vision_model_ocr = "gpt-4o"
    settings.bothub_api_key = "shared-token"
    settings.bothub_api_base_url = "https://openai.bothub.chat/v1"

    enabled, cfg, warning, _warnings = _resolve_vlm_configuration()
    assert enabled is True
    assert warning is None
    assert cfg["api_key"] == "shared-token"
    assert cfg["base_url"] == "https://openai.bothub.chat/v1"


def test_vision_provider_openrouter_uses_legacy_settings() -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.vision_provider = "openrouter"
    settings.openrouter_api_key = "token"
    settings.openrouter_model_ocr_vlm = "openrouter-vlm"
    settings.openrouter_ocr_model = ""

    enabled, cfg, warning, _warnings = _resolve_vlm_configuration()
    assert enabled is True
    assert warning is None
    assert cfg["provider"] == "openrouter"
    assert cfg["api_key"] == "token"
    assert cfg["model"] == "openrouter-vlm"


def test_vision_provider_disabled_disables_vlm() -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.vision_provider = "disabled"

    enabled, _cfg, warning, _warnings = _resolve_vlm_configuration()
    assert enabled is False
    assert warning is not None
    assert "отключ" in warning.lower()


def test_ocr_use_vlm_false_disables_vlm_regardless_provider() -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = False
    settings.vision_provider = "bothub"
    settings.bothub_api_key = "token"
    settings.vision_model_ocr = "gpt-4o"

    enabled, _cfg, warning, _warnings = _resolve_vlm_configuration()
    assert enabled is False
    assert warning is not None
    assert "настройк" in warning.lower()
