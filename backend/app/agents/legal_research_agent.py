from __future__ import annotations

import json
import logging
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.openrouter_service import extract_json_from_chat_response, post_chat_completion

logger = logging.getLogger(__name__)

LEGAL_DISCLAIMER = (
    "Поиск выполняется только по публично доступным страницам. "
    "Система не гарантирует полный доступ к коммерческим базам "
    "КонсультантПлюс/Гарант и не предоставляет юридическую консультацию."
)

SourceType = Literal[
    "consultant_plus", "garant", "pravo_gov", "other_public_source"
]
RelevanceType = Literal["low", "medium", "high", "unknown"]


class LegalSourceItem(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: SourceType
    relevance: RelevanceType = "unknown"


class LegalResearchLLMResponse(BaseModel):
    legal_sources: list[LegalSourceItem] = Field(default_factory=list)
    limitations: str = ""


SYSTEM_PROMPT = """You are a legal research assistant for contract analysis previews.
Use the openrouter:web_search tool to find publicly accessible references on allowed legal domains only.
Do not claim full access to Consultant Plus or Garant commercial databases.
Do not provide legal advice.
Return ONLY valid JSON matching the requested schema after reviewing search results.
"""


def parse_allowed_domains(raw: str | None = None) -> list[str]:
    value = raw if raw is not None else settings.legal_allowed_domains
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def classify_source_type(url: str) -> SourceType:
    host = urlparse(url).netloc.lower()
    if "consultant.ru" in host:
        return "consultant_plus"
    if "garant.ru" in host:
        return "garant"
    if "pravo.gov.ru" in host:
        return "pravo_gov"
    return "other_public_source"


def url_matches_allowed_domains(url: str, allowed_domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return False
    return any(domain in host for domain in allowed_domains)


def build_search_queries(
    summary: str,
    risks: list[dict[str, Any]],
    key_terms: list[dict[str, Any]],
) -> list[str]:
    queries: list[str] = [
        "расторжение договора одностороннее расторжение условия",
        "ответственность сторон штрафы неустойка договор",
        "оплата сроки исполнения договорные обязательства",
    ]

    for risk in risks[:2]:
        title = str(risk.get("title") or risk.get("type") or "").strip()
        explanation = str(risk.get("explanation") or risk.get("description") or "").strip()
        fragment = title or explanation[:120]
        if fragment:
            queries.append(f"рискованная формулировка договора {fragment}")

    if summary.strip():
        queries.append(f"правовое регулирование условий договора {summary[:160]}")

    unique: list[str] = []
    for query in queries:
        normalized = query.strip()
        if normalized and normalized not in unique:
            unique.append(normalized)
        if len(unique) >= 4:
            break
    return unique[:4]


def _build_web_search_tool(allowed_domains: list[str]) -> dict[str, Any]:
    return {
        "type": "openrouter:web_search",
        "parameters": {
            "max_results": settings.legal_search_max_results,
            "search_context_size": settings.legal_search_context_size,
            "allowed_domains": allowed_domains,
        },
    }


def _build_user_prompt(
    document_id: str,
    summary: str,
    risks: list[dict[str, Any]],
    key_terms: list[dict[str, Any]],
    search_queries: list[str],
) -> str:
    return f"""Document ID: {document_id}

Contract summary:
{summary or "N/A"}

Identified risks (JSON):
{json.dumps(risks[:8], ensure_ascii=False)}

Key terms (JSON):
{json.dumps(key_terms[:8], ensure_ascii=False)}

Perform web search for these query themes (use web_search tool as needed):
{json.dumps(search_queries, ensure_ascii=False)}

Return JSON:
{{
  "legal_sources": [
    {{
      "title": "string",
      "url": "string",
      "snippet": "string",
      "source_type": "consultant_plus | garant | pravo_gov | other_public_source",
      "relevance": "low | medium | high | unknown"
    }}
  ],
  "limitations": "string describing coverage limits and that sources are public previews only"
}}

Only include sources whose URLs are on allowed domains: {", ".join(parse_allowed_domains())}.
If no reliable public sources found, return legal_sources=[] and explain in limitations.
"""


def _normalize_sources(
    sources: list[LegalSourceItem],
    allowed_domains: list[str],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in sources:
        url = item.url.strip()
        if not url or url in seen_urls:
            continue
        if not url_matches_allowed_domains(url, allowed_domains):
            continue

        source_type = classify_source_type(url)

        seen_urls.add(url)
        normalized.append(
            {
                "title": item.title.strip() or url,
                "url": url,
                "snippet": item.snippet.strip(),
                "source_type": source_type,
                "relevance": item.relevance,
            }
        )
    return normalized


def _empty_result(limitations: str, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "legal_sources": [],
        "limitations": limitations,
        "warnings": warnings or [limitations],
        "provider": settings.legal_search_provider,
        "allowed_domains": settings.legal_allowed_domains,
    }


class LegalResearchAgent:
    def run(
        self,
        document_id: str,
        risks: list[dict[str, Any]],
        key_terms: list[dict[str, Any]],
        summary: str,
    ) -> dict[str, Any]:
        allowed_domains = parse_allowed_domains()

        if not settings.legal_web_search_enabled:
            return _empty_result("Legal web search disabled by configuration.")

        if settings.legal_search_provider != "openrouter_web_search":
            return _empty_result(
                f"Unsupported legal search provider: {settings.legal_search_provider}."
            )

        if not settings.openrouter_api_key:
            return _empty_result("Legal web search provider is unavailable.")

        search_queries = build_search_queries(summary, risks, key_terms)
        user_prompt = _build_user_prompt(
            document_id=document_id,
            summary=summary,
            risks=risks,
            key_terms=key_terms,
            search_queries=search_queries,
        )

        try:
            response_data = post_chat_completion(
                model=settings.openrouter_model_legal_research,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_build_web_search_tool(allowed_domains)],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            parsed = extract_json_from_chat_response(response_data)
            validated = LegalResearchLLMResponse.model_validate(parsed)
        except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning("Legal web search failed: %s", exc)
            return _empty_result("Legal web search provider is unavailable.")

        sources = _normalize_sources(validated.legal_sources, allowed_domains)
        limitations = validated.limitations.strip() or LEGAL_DISCLAIMER
        if not sources:
            limitations = (
                f"{limitations} No public legal sources were matched on allowed domains."
            ).strip()

        warnings = [limitations, LEGAL_DISCLAIMER]
        return {
            "legal_sources": sources,
            "limitations": limitations,
            "warnings": warnings,
            "provider": settings.legal_search_provider,
            "allowed_domains": settings.legal_allowed_domains,
        }
