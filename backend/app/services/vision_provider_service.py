from __future__ import annotations

import base64
import json
import logging
from typing import Any

from app.config import settings
from app.services.llm_provider_service import post_chat_completion_text
from app.services.ocr_text_validation import looks_like_valid_ocr_text
from app.services.provider_errors import ProviderError, get_openrouter_legacy_code

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = (
    "Ты OCR-система для извлечения текста из страниц договора. "
    "Твоя задача — распознать весь видимый текст на изображении. "
    "Верни только распознанный текст. "
    "Не пересказывай. Не анализируй договор. Не делай юридические выводы. "
    "Не добавляй комментарии. Не описывай изображение. "
    "Не добавляй markdown. Не добавляй JSON. "
    "Сохраняй русский язык и кириллицу. "
    "Сохраняй порядок строк насколько возможно. "
    "Если фрагмент неразборчив, напиши [неразборчиво]."
)

VISION_USER_TEXT = (
    "Извлеки весь видимый текст с этой страницы договора. "
    "Ответ должен содержать только OCR-текст страницы, без пояснений и без анализа."
)


def _extract_text_from_json_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("text", "ocr_text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_text_from_string_content(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""

    if cleaned.startswith("```") and cleaned.endswith("```"):
        inner = cleaned[3:-3].strip()
        if inner.lower().startswith("json"):
            inner = inner[4:].strip()
        cleaned = inner

    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return cleaned
        text_from_json = _extract_text_from_json_payload(payload)
        return text_from_json or ""
    return cleaned


def _collect_text_candidates(value: object) -> list[str]:
    if isinstance(value, str):
        candidate = _extract_text_from_string_content(value)
        return [candidate] if candidate else []

    if isinstance(value, list):
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_text_candidates(item))
        return collected

    if isinstance(value, dict):
        collected: list[str] = []
        for key in ("text", "output_text", "content"):
            nested = value.get(key)
            if isinstance(nested, str):
                candidate = _extract_text_from_string_content(nested)
                if candidate:
                    collected.append(candidate)
            elif isinstance(nested, (list, dict)):
                collected.extend(_collect_text_candidates(nested))
        return collected

    return []


def _bad_response_error(provider: str, message: str) -> ProviderError:
    legacy_code = None
    if provider == "openrouter":
        legacy_code = get_openrouter_legacy_code("provider_bad_response")
    return ProviderError(
        provider=provider,
        code="provider_bad_response",
        legacy_code=legacy_code,
        message=message,
        status_code=None,
        retryable=False,
    )


def _pick_best_text_candidate(candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate.strip():
            return candidate.strip()
    return ""


def extract_text_from_image_with_vision_provider(
    *,
    image_bytes: bytes,
    page_number: int,
    model: str,
    provider: str,
    base_url: str,
    api_key: str,
    timeout: float = 120,
    include_usage: bool = False,
) -> str:
    base64_image = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{base64_image}"
    user_text = f"{VISION_USER_TEXT}\nPage number: {page_number}."

    extra_body: dict[str, Any] | None = None
    if provider == "bothub" and include_usage:
        extra_body = {"bothub": {"include_usage": True}}

    data = post_chat_completion_text(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0,
        timeout=timeout,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        extra_body=extra_body,
        stage="ocr_vlm",
    )

    try:
        choice = data["choices"][0]
        message = choice["message"]
        message_content = message.get("content")
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise _bad_response_error(
            provider,
            f"Unexpected {provider.capitalize()} response format.",
        ) from exc

    primary_candidates = _collect_text_candidates(message_content)
    extracted = _pick_best_text_candidate(primary_candidates)
    if extracted:
        return extracted

    reasoning_candidate = ""
    for key in ("reasoning_content", "reasoning"):
        maybe_reasoning = message.get(key)
        if isinstance(maybe_reasoning, str) and maybe_reasoning.strip():
            reasoning_candidate = maybe_reasoning.strip()
            break
    if not reasoning_candidate and isinstance(choice, dict):
        for key in ("reasoning_content", "reasoning"):
            maybe_reasoning = choice.get(key)
            if isinstance(maybe_reasoning, str) and maybe_reasoning.strip():
                reasoning_candidate = maybe_reasoning.strip()
                break

    if reasoning_candidate:
        min_chars = max(20, int(settings.ocr_min_text_chars_per_page or 50) // 2)
        valid, reason = looks_like_valid_ocr_text(reasoning_candidate, min_chars=min_chars)
        if valid:
            logger.info(
                "ocr_vlm reasoning fallback accepted provider=%s model=%s source=reasoning_content_fallback len=%d",
                provider,
                model,
                len(reasoning_candidate),
            )
            return reasoning_candidate
        logger.info(
            "ocr_vlm reasoning fallback rejected provider=%s model=%s reason=%s len=%d",
            provider,
            model,
            reason,
            len(reasoning_candidate),
        )

    return ""
