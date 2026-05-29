import json
import base64

import httpx

from app.config import settings

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
        raise ValueError("Model returned invalid JSON response.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object.")
    return parsed


def _post_openrouter(model: str, messages: list[dict], temperature: float = 0.2) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                settings.openrouter_base_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("OpenRouter request failed.") from exc

    data = response.json()
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected OpenRouter response format.") from exc


def _call_with_fallback(
    primary_model: str, messages: list[dict], temperature: float = 0.2
) -> str:
    try:
        return _post_openrouter(
            model=primary_model,
            messages=messages,
            temperature=temperature,
        )
    except Exception:
        return _post_openrouter(
            model=settings.openrouter_model_fallback,
            messages=messages,
            temperature=temperature,
        )


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


def ask_llm_json(system_prompt: str, user_prompt: str, model: str) -> dict:
    content = _call_with_fallback(
        primary_model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
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
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    resolved_model = (
        model
        or settings.openrouter_model_ocr_vlm
        or settings.openrouter_ocr_model
    )
    if not resolved_model:
        raise RuntimeError("OPENROUTER_MODEL_OCR_VLM is not configured.")

    base64_image = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{base64_image}"
    prompt = (
        "Извлеки весь видимый текст со страницы документа. "
        "Сохрани порядок чтения и исходный язык. "
        "Не добавляй комментарии, не переводи и не интерпретируй текст. "
        "Ответ верни только plain text без markdown."
    )

    payload = {
        "model": resolved_model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}\nНомер страницы: {page_number}."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=float(settings.ocr_vlm_timeout_seconds)) as client:
            response = client.post(
                settings.openrouter_base_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("OpenRouter VLM OCR request failed.") from exc

    data = response.json()
    try:
        message_content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected OpenRouter VLM OCR response format.") from exc

    extracted = _extract_text_content(message_content)
    return extracted.strip()
