from __future__ import annotations

from pathlib import Path


def test_env_example_contains_only_primary_api_key_fields() -> None:
    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    assert "BOTHUB_API_KEY=" in content
    assert "OPENROUTER_API_KEY=" in content

    assert "LLM_API_KEY=" not in content
    assert "VISION_API_KEY=" not in content
    assert "LEGAL_RESEARCH_API_KEY=" not in content
    assert "PERPLEXITY_API_KEY=" not in content


def test_env_example_does_not_expose_layer_specific_base_urls() -> None:
    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    assert "BOTHUB_API_BASE_URL=" in content
    assert "LLM_API_BASE_URL=" not in content
    assert "VISION_API_BASE_URL=" not in content
    assert "LEGAL_RESEARCH_API_BASE_URL=" not in content
    assert "PERPLEXITY_API_BASE_URL=" not in content
