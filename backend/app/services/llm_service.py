import json

import httpx

from app.config import settings

SYSTEM_PROMPT = (
    "You are an AI contract risk analyzer. "
    "Analyze the contract text and return only valid JSON."
)

USER_PROMPT_TEMPLATE = """Analyze this contract context and return JSON with:
{{
  "summary": "short contract summary",
  "risks": [
    {{
      "type": "risk type",
      "severity": "low|medium|high|critical",
      "description": "risk description",
      "recommendation": "what to check or improve"
    }}
  ]
}}

The response must be valid JSON only.

Contract context:
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


def analyze_contract(context: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    payload = {
        "model": settings.openrouter_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)},
        ],
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
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected OpenRouter response format.") from exc

    result = _extract_json_payload(content)
    result.setdefault("summary", "")
    result.setdefault("risks", [])
    return result
