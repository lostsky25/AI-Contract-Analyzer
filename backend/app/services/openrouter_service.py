import json
from typing import Any

import httpx

from app.config import settings


def _extract_message_content(data: dict[str, Any]) -> str:
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected OpenRouter response format.") from exc


def post_chat_completion(
    model: str,
    messages: list[dict[str, str]],
    *,
    tools: list[dict[str, Any]] | None = None,
    response_format: dict[str, str] | None = None,
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

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

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            settings.openrouter_base_url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("OpenRouter response must be a JSON object.")
    return data


def extract_json_from_chat_response(data: dict[str, Any]) -> dict[str, Any]:
    content = _extract_message_content(data)
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object.")
    return parsed
