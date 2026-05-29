import json

import httpx

from app.config import settings

SYSTEM_PROMPT = (
    "Ты — ИИ-анализатор рисков по договорам. "
    "Анализируй текст договора и возвращай только валидный JSON. "
    "Все текстовые поля в JSON (summary, type, description, recommendation) пиши только на русском языке."
)

USER_PROMPT_TEMPLATE = """Проанализируй фрагменты договора и верни JSON:
{{
  "summary": "краткое резюме договора на русском",
  "risks": [
    {{
      "type": "тип риска на русском",
      "severity": "low|medium|high|critical",
      "description": "описание риска на русском",
      "recommendation": "что проверить или улучшить на русском"
    }}
  ]
}}

Ответ — только валидный JSON. Все описания — на русском языке.

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
