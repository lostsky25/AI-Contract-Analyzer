from typing import Any

from pydantic import ValidationError

from app.models.schemas import ContractReport

DISCLAIMER = (
    "Система выполняет предварительный анализ и не заменяет "
    "профессионального юриста."
)
_SEVERITY_VALUES = {"low", "medium", "high", "unknown"}
_SOURCE_TYPE_VALUES = {
    "consultant_plus",
    "garant",
    "pravo_gov",
    "other_public_source",
}
_RELEVANCE_VALUES = {"low", "medium", "high", "unknown"}


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in _SEVERITY_VALUES else "unknown"


def _normalize_source_type(value: Any, url: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _SOURCE_TYPE_VALUES:
        return normalized
    lowered_url = url.lower()
    if "consultant.ru" in lowered_url:
        return "consultant_plus"
    if "garant.ru" in lowered_url:
        return "garant"
    if "pravo.gov.ru" in lowered_url:
        return "pravo_gov"
    return "other_public_source"


def _normalize_relevance(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in _RELEVANCE_VALUES else "unknown"


def _normalize_risk(risk: dict[str, Any]) -> dict[str, Any]:
    explanation = str(
        risk.get("explanation") or risk.get("description") or ""
    ).strip()
    quote = str(risk.get("quote") or explanation).strip()
    return {
        "title": str(risk.get("title") or risk.get("type") or "Risk").strip() or "Risk",
        "severity": _normalize_severity(risk.get("severity")),
        "explanation": explanation,
        "quote": quote or "Цитата не указана.",
        "page": risk.get("page"),
    }


def _normalize_key_term(term: dict[str, Any]) -> dict[str, Any]:
    value = str(term.get("value") or "").strip()
    quote = str(term.get("quote") or value).strip()
    return {
        "title": str(term.get("title") or "Key term").strip() or "Key term",
        "value": value or "Не указано",
        "quote": quote or "Цитата не указана.",
        "page": term.get("page"),
    }


def _normalize_legal_source(source: dict[str, Any]) -> dict[str, Any] | None:
    url = str(source.get("url") or "").strip()
    if not url:
        return None
    title = str(source.get("title") or "").strip() or url
    snippet = str(source.get("snippet") or "").strip()
    source_type = _normalize_source_type(source.get("source_type"), url)
    relevance = _normalize_relevance(source.get("relevance"))
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source_type": source_type,
        "relevance": relevance,
    }


def _dedupe(items: list[dict[str, Any]], key_builder) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = key_builder(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


class ReportAgent:
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = dict(payload or {})
        raw_warnings = report.get("warnings", [])
        if isinstance(raw_warnings, list):
            warnings = [str(item).strip() for item in raw_warnings if str(item).strip()]
        else:
            warnings = ["Invalid warnings format; fallback to empty list."]

        raw_risks = report.get("risks", [])
        if not isinstance(raw_risks, list):
            warnings.append("Invalid risks format; fallback to empty list.")
            raw_risks = []
        normalized_risks = [_normalize_risk(item) for item in raw_risks if isinstance(item, dict)]
        normalized_risks = _dedupe(
            normalized_risks,
            lambda risk: (
                str(risk.get("title", "")).strip().lower(),
                str(risk.get("severity", "")).strip().lower(),
                str(risk.get("explanation", "")).strip().lower(),
                str(risk.get("quote", "")).strip().lower(),
                str(risk.get("page", "")),
            ),
        )

        raw_terms = report.get("key_terms", [])
        if not isinstance(raw_terms, list):
            warnings.append("Invalid key_terms format; fallback to empty list.")
            raw_terms = []
        normalized_terms = [_normalize_key_term(item) for item in raw_terms if isinstance(item, dict)]
        normalized_terms = _dedupe(
            normalized_terms,
            lambda term: (
                str(term.get("title", "")).strip().lower(),
                str(term.get("value", "")).strip().lower(),
                str(term.get("quote", "")).strip().lower(),
                str(term.get("page", "")),
            ),
        )

        raw_sources = report.get("legal_sources", [])
        if not isinstance(raw_sources, list):
            warnings.append("Invalid legal_sources format; fallback to empty list.")
            raw_sources = []
        normalized_sources: list[dict[str, Any]] = []
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            normalized = _normalize_legal_source(source)
            if normalized is not None:
                normalized_sources.append(normalized)
        normalized_sources = _dedupe(
            normalized_sources,
            lambda source: (
                str(source.get("url", "")).strip().lower(),
                str(source.get("title", "")).strip().lower(),
            ),
        )

        normalized_report = {
            "document_id": str(report.get("document_id", "")).strip(),
            "status": str(report.get("status", "done")).strip().lower(),
            "summary": str(report.get("summary", "")).strip(),
            "overall_risk": str(report.get("overall_risk", "unknown")).strip().lower(),
            "risks": normalized_risks,
            "key_terms": normalized_terms,
            "legal_sources": normalized_sources,
            "warnings": warnings,
            "disclaimer": DISCLAIMER,
            "used_ocr": bool(report.get("used_ocr", False)),
            "chunks_count": int(report.get("chunks_count", 0) or 0),
        }

        if normalized_report["status"] not in {"failed", "processing"} and warnings:
            normalized_report["status"] = "done_with_warnings"

        if not normalized_report["document_id"]:
            normalized_report["document_id"] = "unknown_document"
            normalized_report["status"] = "done_with_warnings"
            normalized_report["warnings"].append(
                "Missing document_id; fallback report was generated."
            )

        try:
            validated = ContractReport.model_validate(normalized_report)
            return validated.model_dump(mode="json")
        except (ValidationError, TypeError, ValueError):
            fallback = {
                "document_id": normalized_report["document_id"] or "unknown_document",
                "status": "done_with_warnings",
                "summary": normalized_report["summary"],
                "overall_risk": "unknown",
                "risks": [],
                "key_terms": [],
                "legal_sources": [],
                "warnings": normalized_report["warnings"]
                + ["Report normalization fallback was applied."],
                "disclaimer": DISCLAIMER,
                "used_ocr": bool(normalized_report.get("used_ocr", False)),
                "chunks_count": int(normalized_report.get("chunks_count", 0)),
            }
            validated_fallback = ContractReport.model_validate(fallback)
            return validated_fallback.model_dump(mode="json")
