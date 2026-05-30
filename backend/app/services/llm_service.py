import json
import base64
import logging


from app.config import settings
from app.services.openrouter_service import ProviderError, post_chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — ИИ-анализатор рисков по договорам. "
    "Анализируй текст договора и возвращай только валидный JSON. "
    "Пользовательские поля summary/type/description/recommendation пиши на русском языке. "
    "Цитаты должны оставаться дословными фрагментами исходного договора."
)

USER_PROMPT_TEMPLATE = """Проанализируй фрагменты договора и верни JSON:
{{
  "summary": "краткое резюме договора на русском языке",
  "risks": [
    {{
      "type": "название риска на русском языке",
      "severity": "low|medium|high|unknown",
      "description": "описание риска на русском языке",
      "recommendation": "что проверить или улучшить на русском языке"
    }}
  ]
}}

Обязательные правила:
1. Не используй английские названия рисков и объяснения.
2. Не смешивай русский и английский в одном предложении, кроме названий компаний и терминов договора.
3. Ответ — только валидный JSON.

Контекст договора:
{context}
"""


def _extract_json_payload(content: str) -> dict:
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


def _post_openrouter(model: str, messages: list[dict], temperature: float = 0.2) -> str:
    data = post_chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        timeout=60.0,
    )
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


def _call_with_fallback(
    primary_model: str, messages: list[dict], temperature: float = 0.2
) -> str:
    try:
        return _post_openrouter(
            model=primary_model,
            messages=messages,
            temperature=temperature,
        )
    except ProviderError as exc:
        if exc.code in {"openrouter_missing_key", "openrouter_auth_failed"}:
            raise
    except Exception:
        pass
    try:
        return _post_openrouter(
            model=settings.openrouter_model_fallback,
            messages=messages,
            temperature=temperature,
        )
    except ProviderError as exc:
        raise exc


def analyze_contract(context: str, model: str | None = None) -> dict:
    content = _call_with_fallback(
        primary_model=model or settings.openrouter_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)},
        ],
    )
    result = _extract_json_payload(content)
    result.setdefault("summary", "")
    result.setdefault("risks", [])
    return result


def ask_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.2,
) -> dict:
    content = _call_with_fallback(
        primary_model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return _extract_json_payload(content)


def ask_llm_text(system_prompt: str, user_prompt: str, model: str) -> str:
    return _call_with_fallback(
        primary_model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    ).strip()


def _extract_text_content(message_content: object) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        text_parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict):
                item_text = item.get("text")
                if isinstance(item_text, str):
                    text_parts.append(item_text)
        return "\n".join(part for part in text_parts if part).strip()
    return ""


def extract_text_from_image_with_vlm(
    image_bytes: bytes,
    page_number: int,
    model: str | None = None,
) -> str:
    explicit_model = str(model or "").strip()
    preferred_model = str(settings.openrouter_model_ocr_vlm or "").strip()
    legacy_model = str(settings.openrouter_ocr_model or "").strip()

    if explicit_model:
        resolved_model = explicit_model
    elif preferred_model:
        resolved_model = preferred_model
    else:
        resolved_model = legacy_model
        if resolved_model:
            logger.warning(
                "OPENROUTER_MODEL_OCR_VLM is not set; using legacy OPENROUTER_OCR_MODEL."
            )

    if not resolved_model:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_model_not_found",
            message="OpenRouter model is not available.",
            status_code=None,
            retryable=False,
        )

    base64_image = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{base64_image}"
    system_prompt = (
        "You are an OCR system. Extract all visible text from the page, preserve reading order, "
        "do not translate, do not add comments, and do not reinterpret legal meaning. "
        "Return plain text only."
    )
    prompt = (
        "Extract every visible character from this contract page. "
        "Keep original language and layout order. "
        "If text is Russian, keep it in Russian. "
        "Return only plain text without markdown."
    )

    data = post_chat_completion(
        model=resolved_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}\nPage number: {page_number}."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=0,
        timeout=float(settings.ocr_vlm_timeout_seconds),
    )
    try:
        message_content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            provider="openrouter",
            code="openrouter_bad_response",
            message="Unexpected OpenRouter response format.",
            status_code=None,
            retryable=False,
        ) from exc

    extracted = _extract_text_content(message_content)
    return extracted.strip()
