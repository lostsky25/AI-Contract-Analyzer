from __future__ import annotations

import base64
import httpx
import pytest

from app.services.provider_errors import ProviderError
from app.services.vision_provider_service import extract_text_from_image_with_vision_provider


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
    captured: dict[str, object] = {}

    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, tb):
            return False

        def post(self, _url: str, *, headers: dict, json: dict):
            captured["headers"] = headers
            captured["payload"] = json
            return response

    monkeypatch.setattr("app.services.llm_provider_service.httpx.Client", _Client)
    return captured


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


def test_bothub_vision_200_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            status_code=200,
            payload={"choices": [{"message": {"content": "OCR text"}}]},
        ),
    )
    result = extract_text_from_image_with_vision_provider(
        image_bytes=b"abc",
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert result == "OCR text"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    image_url = payload["messages"][1]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    assert base64.b64encode(b"abc").decode("ascii") in image_url


def test_bothub_vision_401_maps_to_provider_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(monkeypatch, _DummyResponse(401, {"error": {"message": "unauthorized"}}))
    with pytest.raises(ProviderError) as exc_info:
        extract_text_from_image_with_vision_provider(
            image_bytes=b"abc",
            page_number=1,
            model="gpt-4o",
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
        )
    assert exc_info.value.code == "provider_auth_failed"


def test_bothub_vision_429_maps_to_provider_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(monkeypatch, _DummyResponse(429, {"error": {"message": "rate limit"}}))
    with pytest.raises(ProviderError) as exc_info:
        extract_text_from_image_with_vision_provider(
            image_bytes=b"abc",
            page_number=1,
            model="gpt-4o",
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
        )
    assert exc_info.value.code == "provider_rate_limited"


def test_bothub_vision_404_maps_to_provider_model_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(monkeypatch, _DummyResponse(404, {"error": {"message": "model not found"}}))
    with pytest.raises(ProviderError) as exc_info:
        extract_text_from_image_with_vision_provider(
            image_bytes=b"abc",
            page_number=1,
            model="missing",
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
        )
    assert exc_info.value.code == "provider_model_not_found"


def test_bothub_vision_timeout_maps_to_provider_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_exception(monkeypatch, httpx.TimeoutException("timeout"))
    with pytest.raises(ProviderError) as exc_info:
        extract_text_from_image_with_vision_provider(
            image_bytes=b"abc",
            page_number=1,
            model="gpt-4o",
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
        )
    assert exc_info.value.code == "provider_timeout"


def test_bothub_vision_malformed_response_maps_to_provider_bad_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_client_with_response(monkeypatch, _DummyResponse(200, {"not_choices": []}))
    with pytest.raises(ProviderError) as exc_info:
        extract_text_from_image_with_vision_provider(
            image_bytes=b"abc",
            page_number=1,
            model="gpt-4o",
            provider="bothub",
            base_url="https://openai.bothub.chat/v1",
            api_key="token",
        )
    assert exc_info.value.code == "provider_bad_response"


def test_vision_parser_extracts_text_from_output_text_block(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "output_text", "output_text": "Текст из output_text блока."}
                            ]
                        }
                    }
                ]
            },
        ),
    )
    result = extract_text_from_image_with_vision_provider(
        image_bytes=b"abc",
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert "output_text" in result


def test_vision_parser_extracts_text_from_json_text_field(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            200,
            {"choices": [{"message": {"content": "{\"text\": \"Текст из JSON поля.\"}"}}]},
        ),
    )
    result = extract_text_from_image_with_vision_provider(
        image_bytes=b"abc",
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert result == "Текст из JSON поля."


def test_vision_parser_reasoning_content_only_used_if_valid_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": "На изображении видно договор и условия сторон.",
                        }
                    }
                ]
            },
        ),
    )
    rejected = extract_text_from_image_with_vision_provider(
        image_bytes=b"abc",
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert rejected == ""

    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": "ДОГОВОР ПОСТАВКИ от 12.01.2026. Стороны согласовали сроки оплаты.",
                        }
                    }
                ]
            },
        ),
    )
    accepted = extract_text_from_image_with_vision_provider(
        image_bytes=b"abc",
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert "ДОГОВОР ПОСТАВКИ" in accepted


def test_vision_client_does_not_log_base64(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = b"do-not-log-this"
    encoded = base64.b64encode(sample).decode("ascii")
    _patch_client_with_response(
        monkeypatch,
        _DummyResponse(status_code=200, payload={"choices": [{"message": {"content": "ok"}}]}),
    )
    extract_text_from_image_with_vision_provider(
        image_bytes=sample,
        page_number=1,
        model="gpt-4o",
        provider="bothub",
        base_url="https://openai.bothub.chat/v1",
        api_key="token",
    )
    assert encoded not in caplog.text
