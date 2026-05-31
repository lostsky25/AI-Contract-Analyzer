from __future__ import annotations

import json
import re
from typing import Any

MOJIBAKE_MARKERS = (
    "РџС",
    "Р В°",
    "Р Вµ",
    "Р Р…",
    "Р С‘",
    "РЎРѓ",
    "РЎвЂљ",
    "Гђ",
    "Г‘",
    "пїЅ",
)

META_PATTERNS = (
    "на изображении видно",
    "я вижу",
    "this image contains",
    "the image shows",
    "данный договор содержит",
    "в документе говорится",
    "договор предусматривает",
)

REFUSAL_PATTERNS = (
    "извините",
    "i'm unable",
    "cannot read",
    "не могу распознать",
    "не удалось распознать",
    "я не могу",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _unwrap_markdown_code_fence(text: str) -> str:
    raw = text.strip()
    if not (raw.startswith("```") and raw.endswith("```")):
        return raw
    inner = raw[3:-3].strip()
    if inner.lower().startswith("json"):
        inner = inner[4:].strip()
    return inner


def _extract_text_from_json_wrapper(text: str) -> str:
    candidate = text.strip()
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return ""
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in ("text", "ocr_text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def looks_like_valid_ocr_text(text: str, *, min_chars: int = 50) -> tuple[bool, str]:
    raw = str(text or "")
    if not raw.strip():
        return False, "empty"

    unwrapped = _unwrap_markdown_code_fence(raw)
    if not unwrapped.strip():
        return False, "markdown_wrapper_only"

    json_text = _extract_text_from_json_wrapper(unwrapped)
    normalized = _normalize(json_text or unwrapped)
    lowered = normalized.lower()

    if not normalized:
        return False, "empty"
    if any(marker.lower() in lowered for marker in MOJIBAKE_MARKERS):
        return False, "mojibake"
    if any(token in lowered for token in REFUSAL_PATTERNS):
        return False, "refusal"
    if any(token in lowered for token in META_PATTERNS):
        return False, "model_meta_response"

    letters_or_digits = sum(1 for ch in normalized if ch.isalpha() or ch.isdigit())
    punct_or_space = sum(1 for ch in normalized if (not ch.isalnum()))
    if letters_or_digits == 0:
        return False, "no_alnum"

    text_ratio = letters_or_digits / max(1, len(normalized))
    if text_ratio < 0.25:
        return False, "low_text_ratio"
    if punct_or_space / max(1, len(normalized)) > 0.85:
        return False, "mostly_noise"

    if len(normalized) < int(min_chars):
        if len(normalized) < 20:
            return False, "too_short"
        if text_ratio < 0.55:
            return False, "too_short_low_ratio"
        return True, "ok_short"

    return True, "ok"

