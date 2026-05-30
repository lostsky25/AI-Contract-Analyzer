import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


@dataclass
class ProviderError(ValueError):
    provider: str
    code: str
    message: str
    status_code: int | None = None
    retryable: bool = False
    raw_detail: str | None = None

    def __str__(self) -> str:
        return self.message


def _sanitize_detail(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error_value = payload.get("error")
        if isinstance(error_value, dict):
            message = error_value.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:240]
        if isinstance(error_value, str) and error_value.strip():
            return error_value.strip()[:240]
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:240]
    if isinstance(payload, str) and payload.strip():
        return payload.strip()[:240]
    return None


def _build_provider_error(
    *,
    status_code: int | None,
    detail_text: str | None = None,
) -> ProviderError:
    lowered = (detail_text or "").lower()
    if status_code in {401, 403}:
        return ProviderError(
            provider="openrouter",
            code="openrouter_auth_failed",
            message="OpenRouter authentication failed.",
            status_code=status_code,
            retryable=False,
            raw_detail=detail_text,
        )
    if status_code == 429:
        return ProviderError(
            provider="openrouter",
            code="openrouter_rate_limited",
            message="OpenRouter rate limit exceeded.",
            status_code=status_code,
            retryable=True,
            raw_detail=detail_text,
        )
    if status_code == 404 or "no endpoints found" in lowered:
        return ProviderError(
            provider="openrouter",
            code="openrouter_model_not_found",
            message="OpenRouter model is not available.",
            status_code=status_code,
            retryable=False,
            raw_detail=detail_text,
        )
    if status_code is not None and status_code >= 500:
        return ProviderError(
            provider="openrouter",
            code="openrouter_unavailable",
            message="OpenRouter service is temporarily unavailable.",
            status_code=status_code,
            retryable=True,
            raw_detail=detail_text,
        )
    return ProviderError(
        provider="openrouter",
        code="openrouter_unknown_error",
        message="OpenRouter request failed.",
        status_code=status_code,
        retryable=False,
        raw_detail=detail_text,
    )


def _extract_message_content(data: dict[str, Any]) -> str:
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="Unexpected OpenRouter response format.",
            status_code=None,
            retryable=False,
        ) from exc


def post_chat_completion(
    model: str,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    response_format: dict[str, str] | None = None,
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_missing_key",
            message="OpenRouter API key is not configured.",
            status_code=None,
            retryable=False,
        )

    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                settings.openrouter_base_url,
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_timeout",
            message="OpenRouter request timed out.",
            status_code=None,
            retryable=True,
        ) from exc
    except httpx.RequestError as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_unavailable",
            message="OpenRouter service is temporarily unavailable.",
            status_code=None,
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        detail_text: str | None = None
        try:
            detail_text = _sanitize_detail(response.json())
        except Exception:
            detail_text = _sanitize_detail(response.text)
        raise _build_provider_error(
            status_code=response.status_code,
            detail_text=detail_text,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="Unexpected OpenRouter response format.",
            status_code=response.status_code,
            retryable=False,
        ) from exc
    if not isinstance(data, dict):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="OpenRouter response must be a JSON object.",
            status_code=response.status_code,
            retryable=False,
        )
    return data


def extract_json_from_chat_response(data: dict[str, Any]) -> dict[str, Any]:
    content = _extract_message_content(data)
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="Unexpected OpenRouter response format.",
            status_code=None,
            retryable=False,
        ) from exc
    if not isinstance(parsed, dict):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="Model response must be a JSON object.",
            status_code=None,
            retryable=False,
        )
    return parsed
