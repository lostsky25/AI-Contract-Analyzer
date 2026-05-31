from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.provider_errors import ProviderError, get_openrouter_legacy_code

logger = logging.getLogger(__name__)


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


def _legacy_code_for(provider: str, generic_code: str) -> str | None:
    if provider == "openrouter":
        return get_openrouter_legacy_code(generic_code)
    return None


def _provider_error(
    *,
    provider: str,
    code: str,
    message: str,
    status_code: int | None = None,
    retryable: bool = False,
    raw_detail: str | None = None,
) -> ProviderError:
    return ProviderError(
        provider=provider,
        code=code,
        message=message,
        status_code=status_code,
        retryable=retryable,
        raw_detail=raw_detail,
        legacy_code=_legacy_code_for(provider, code),
    )


def _build_provider_error(
    *,
    provider: str,
    status_code: int | None,
    detail_text: str | None = None,
) -> ProviderError:
    lowered = (detail_text or "").lower()
    if status_code in {401, 403}:
        return _provider_error(
            provider=provider,
            code="provider_auth_failed",
            message=f"{provider.capitalize()} authentication failed.",
            status_code=status_code,
            retryable=False,
            raw_detail=detail_text,
        )
    if status_code == 429:
        return _provider_error(
            provider=provider,
            code="provider_rate_limited",
            message=f"{provider.capitalize()} rate limit exceeded.",
            status_code=status_code,
            retryable=True,
            raw_detail=detail_text,
        )
    if status_code == 404 or "model not found" in lowered or "no endpoints found" in lowered:
        return _provider_error(
            provider=provider,
            code="provider_model_not_found",
            message=f"{provider.capitalize()} model is not available.",
            status_code=status_code,
            retryable=False,
            raw_detail=detail_text,
        )
    if status_code is not None and status_code >= 500:
        return _provider_error(
            provider=provider,
            code="provider_unavailable",
            message=f"{provider.capitalize()} service is temporarily unavailable.",
            status_code=status_code,
            retryable=True,
            raw_detail=detail_text,
        )
    return _provider_error(
        provider=provider,
        code="provider_unknown_error",
        message=f"{provider.capitalize()} request failed.",
        status_code=status_code,
        retryable=False,
        raw_detail=detail_text,
    )


def _build_endpoint(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def _collect_bad_response_diagnostics(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "top_keys": "n/a",
            "choices_count": -1,
            "finish_reason": "n/a",
            "has_message": False,
            "content_type": type(data).__name__,
            "content_length": -1,
            "usage_present": False,
            "bothub_caps_present": False,
            "response_looks_truncated": False,
        }

    choices = data.get("choices")
    choices_count = len(choices) if isinstance(choices, list) else -1
    first_choice = choices[0] if isinstance(choices, list) and choices else {}
    finish_reason = ""
    message: dict[str, Any] | None = None
    if isinstance(first_choice, dict):
        finish_reason = str(first_choice.get("finish_reason") or "")
        maybe_message = first_choice.get("message")
        if isinstance(maybe_message, dict):
            message = maybe_message

    content = message.get("content") if message else None
    content_type = type(content).__name__ if content is not None else "none"
    content_length = -1
    looks_truncated = False
    if isinstance(content, str):
        content_length = len(content)
        looks_truncated = content.rstrip().endswith("...")
    elif isinstance(content, list):
        content_length = len(content)

    return {
        "top_keys": ",".join(list(data.keys())[:10]) or "none",
        "choices_count": choices_count,
        "finish_reason": finish_reason or "none",
        "has_message": bool(message),
        "content_type": content_type,
        "content_length": content_length,
        "usage_present": isinstance(data.get("usage"), dict),
        "bothub_caps_present": isinstance(data.get("bothub"), dict),
        "response_looks_truncated": looks_truncated,
    }


def _log_provider_bad_response(
    *,
    stage: str | None,
    provider: str,
    model: str,
    status_code: int | None,
    parse_error_type: str,
    data: Any,
) -> None:
    diagnostics = _collect_bad_response_diagnostics(data)
    logger.warning(
        (
            "provider_bad_response stage=%s provider=%s model=%s status=%s "
            "top_keys=%s choices_count=%s finish_reason=%s has_message=%s "
            "content_type=%s content_length=%s usage_present=%s bothub_caps_present=%s "
            "parse_error_type=%s response_looks_truncated=%s"
        ),
        stage or "unknown",
        provider,
        model,
        status_code if status_code is not None else "none",
        diagnostics["top_keys"],
        diagnostics["choices_count"],
        diagnostics["finish_reason"],
        diagnostics["has_message"],
        diagnostics["content_type"],
        diagnostics["content_length"],
        diagnostics["usage_present"],
        diagnostics["bothub_caps_present"],
        parse_error_type,
        diagnostics["response_looks_truncated"],
    )


def post_chat_completion_text(
    *,
    messages: list[dict[str, Any]],
    model: str,
    provider: str,
    base_url: str,
    api_key: str,
    temperature: float = 0.2,
    timeout: float = 60.0,
    response_format: dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    if not api_key.strip():
        raise _provider_error(
            provider=provider,
            code="provider_missing_key",
            message=f"{provider.capitalize()} API key is not configured.",
            retryable=False,
        )
    if not base_url.strip():
        raise _provider_error(
            provider=provider,
            code="provider_bad_response",
            message=f"{provider.capitalize()} API base URL is not configured.",
            retryable=False,
        )
    if not model.strip():
        raise _provider_error(
            provider=provider,
            code="provider_model_not_found",
            message=f"{provider.capitalize()} model is not configured.",
            retryable=False,
        )

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format
    if extra_body:
        payload.update(extra_body)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                _build_endpoint(base_url),
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise _provider_error(
            provider=provider,
            code="provider_timeout",
            message=f"{provider.capitalize()} request timed out.",
            retryable=True,
        ) from exc
    except httpx.RequestError as exc:
        raise _provider_error(
            provider=provider,
            code="provider_unavailable",
            message=f"{provider.capitalize()} service is temporarily unavailable.",
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        detail_text: str | None = None
        try:
            detail_text = _sanitize_detail(response.json())
        except Exception:
            detail_text = _sanitize_detail(response.text)
        raise _build_provider_error(
            provider=provider,
            status_code=response.status_code,
            detail_text=detail_text,
        )

    try:
        data = response.json()
    except ValueError as exc:
        _log_provider_bad_response(
            stage=stage,
            provider=provider,
            model=model,
            status_code=response.status_code,
            parse_error_type=type(exc).__name__,
            data=response.text,
        )
        raise _provider_error(
            provider=provider,
            code="provider_bad_response",
            message=f"Unexpected {provider.capitalize()} response format.",
            status_code=response.status_code,
            retryable=False,
        ) from exc

    if not isinstance(data, dict):
        _log_provider_bad_response(
            stage=stage,
            provider=provider,
            model=model,
            status_code=response.status_code,
            parse_error_type="non_dict_payload",
            data=data,
        )
        raise _provider_error(
            provider=provider,
            code="provider_bad_response",
            message=f"{provider.capitalize()} response must be a JSON object.",
            status_code=response.status_code,
            retryable=False,
        )
    return data
