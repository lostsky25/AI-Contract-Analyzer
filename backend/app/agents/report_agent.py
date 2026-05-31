from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.agents.normalization_utils import (
    canonicalize_url,
    classify_source_type_from_url,
    normalize_page,
    normalize_quote,
    normalize_whitespace,
)
from app.models.schemas import ContractReport

DISCLAIMER = "Система выполняет предварительный анализ и не заменяет профессионального юриста."
_SEVERITY_VALUES = {"low", "medium", "high", "unknown"}
_RELEVANCE_VALUES = {"low", "medium", "high", "unknown"}
_MACHINE_SOURCE_LABELS = {
    "consultant_plus": "КонсультантПлюс",
    "garant": "Гарант",
    "pravo_gov": "pravo.gov.ru",
    "other_public_source": "Публичный источник",
}
_RISK_TITLE_MAP = {
    "high penalties and service suspension for late payment": "Высокие штрафы и приостановка услуг за просрочку оплаты",
    "limited liability cap": "Ограничение ответственности",
    "immediate termination right for provider": "Право исполнителя на немедленное расторжение",
}
_WARNING_MAP = {
    "legal web search provider is unavailable.": "Правовая проверка завершилась с предупреждением: публичные правовые источники были недоступны.",
    "legal web search provider is unavailable": "Правовая проверка завершилась с предупреждением: публичные правовые источники были недоступны.",
    "legal web search failed.": "Правовая проверка завершилась с предупреждением: публичные правовые источники были недоступны.",
    "openrouter_api_key is missing.": "Внешний AI-провайдер недоступен.",
    "openrouter request failed.": "Внешний AI-провайдер недоступен.",
    "provider_bad_response": "AI-провайдер вернул ответ в неожиданном формате. Попробуйте повторить анализ или выбрать другую модель.",
    "openrouter_bad_response": "AI-провайдер вернул ответ в неожиданном формате. Попробуйте повторить анализ или выбрать другую модель.",
    "provider_unavailable": "Внешний AI-провайдер временно недоступен. Попробуйте позже.",
    "openrouter_unavailable": "Внешний AI-провайдер временно недоступен. Попробуйте позже.",
    "provider_timeout": "AI-провайдер не ответил вовремя. Попробуйте повторить анализ позже.",
    "openrouter_timeout": "AI-провайдер не ответил вовремя. Попробуйте повторить анализ позже.",
    "provider_rate_limited": "Лимит AI-провайдера временно исчерпан. Повторите попытку позже.",
    "openrouter_rate_limited": "Лимит AI-провайдера временно исчерпан. Повторите попытку позже.",
    "provider_auth_failed": "Ошибка доступа к AI-провайдеру. Проверьте настройки ключа API.",
    "openrouter_auth_failed": "Ошибка доступа к AI-провайдеру. Проверьте настройки ключа API.",
    "provider_missing_key": "AI-провайдер не настроен: отсутствует ключ API.",
    "openrouter_missing_key": "AI-провайдер не настроен: отсутствует ключ API.",
    "provider_model_not_found": "Выбранная AI-модель недоступна. Проверьте конфигурацию модели.",
    "openrouter_model_not_found": "Выбранная AI-модель недоступна. Проверьте конфигурацию модели.",
}


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in _SEVERITY_VALUES else "unknown"


def _normalize_relevance(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in _RELEVANCE_VALUES else "unknown"


def _normalize_warning_text(value: Any) -> str:
    cleaned = normalize_whitespace(value)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered in _WARNING_MAP:
        return _WARNING_MAP[lowered]
    if lowered.startswith("provider_") or lowered.startswith("openrouter_"):
        return "Анализ завершился с предупреждением. Проверьте результат вручную."
    if "model-structured" in lowered or "model_reported" in lowered:
        return "Некоторые правовые источники получены из структурированного ответа модели и требуют ручной проверки."
    if "local ocr fallback" in lowered or "ocr fallback" in lowered:
        return "Часть текста была распознана через резервный OCR, возможны ошибки распознавания."
    if "vision ocr не смог" in lowered or ("vision ocr" in lowered and "резервный ocr" in lowered):
        return "Vision OCR не смог надёжно распознать часть страниц. Использован резервный OCR, возможны ошибки."
    if "часть страниц pdf-скана не удалось распознать" in lowered:
        return "Часть страниц PDF-скана не удалось распознать достаточно качественно."
    if "из pdf-скана удалось извлечь недостаточно текста" in lowered:
        return (
            "Из PDF-скана удалось извлечь недостаточно текста для надёжного анализа. "
            "Проверьте качество скана или используйте файл с текстовым слоем."
        )
    if "vision ocr model is unavailable" in lowered or "vision ocr is unavailable" in lowered:
        return "Vision OCR модель недоступна, использован резервный OCR."
    if "vision ocr timed out" in lowered:
        return "Vision OCR не ответил вовремя, использован резервный OCR."
    if "vision ocr rate limit" in lowered:
        return "Лимит Vision OCR временно исчерпан, использован резервный OCR."
    if "vision ocr provider authentication failed" in lowered:
        return "Ошибка доступа к Vision OCR, использован резервный OCR."
    if "vision ocr provider unavailable" in lowered:
        return "Vision OCR временно недоступен, использован резервный OCR."
    if "vision ocr request failed" in lowered:
        return "Vision OCR завершился с ошибкой, использован резервный OCR."
    if "provider returned text links" in lowered or "plain-text url" in lowered:
        return "Провайдер вернул ссылки без валидной структуры, поэтому они не показаны."
    if "outside allowed domains" in lowered:
        return "Проверка источников вернула ссылки вне разрешенных доменов."
    if "invalid or placeholder" in lowered or "placeholder" in lowered:
        return "Проверка источников вернула невалидные ссылки."
    if "root-domain urls" in lowered:
        return "Проверка источников вернула ссылки только на корневые страницы доменов без конкретного документа."
    if "structured legal response did not contain valid allowed-domain sources" in lowered:
        return "Провайдер вернул структурированный ответ, но в нём не оказалось валидных правовых источников на разрешённых доменах."
    if "no grounded public sources were found" in lowered:
        return "Правовые источники не найдены на разрешённых доменах или web-проверка была недоступна."
    if "no grounded or valid structured sources were returned" in lowered:
        return "Правовая проверка завершилась с предупреждением: поставщик AI не вернул валидный структурированный ответ."
    if "provider response did not include grounded citations/search results" in lowered:
        return "Правовая проверка завершилась с предупреждением: в ответе AI не было подтверждённых ссылок на источники."
    if "source" in lowered and "manual" in lowered and "verification" in lowered:
        return "Некоторые правовые источники требуют ручной проверки."
    if "provider is unavailable" in lowered:
        return "Внешний AI-провайдер недоступен."
    if "legal web search" in lowered and "unavailable" in lowered:
        return "Правовая проверка завершилась с предупреждением: публичные правовые источники были недоступны."
    return cleaned


def _normalize_risk_title(value: Any) -> str:
    cleaned = normalize_whitespace(value)
    if not cleaned:
        return ""
    mapped = _RISK_TITLE_MAP.get(cleaned.strip().lower())
    return mapped or cleaned


def _humanize_source_title(title: str, source_type: str, url: str) -> str:
    cleaned = normalize_whitespace(title)
    if not cleaned or cleaned.strip().lower() in _MACHINE_SOURCE_LABELS:
        return _MACHINE_SOURCE_LABELS.get(source_type, url)
    return cleaned


def _normalize_risk(risk: dict[str, Any]) -> dict[str, Any]:
    explanation = normalize_whitespace(
        risk.get("explanation") or risk.get("description") or ""
    )
    quote = normalize_quote(risk.get("quote"), max_chars=420, max_sentences=3)
    title = _normalize_risk_title(risk.get("title") or risk.get("type") or "Риск")

    if quote and explanation.lower() == quote.lower():
        explanation = ""
    if not explanation:
        explanation = "Требуется ручная проверка формулировки договора."

    return {
        "title": title or "Риск",
        "severity": _normalize_severity(risk.get("severity")),
        "explanation": explanation,
        "quote": quote,
        "page": normalize_page(risk.get("page")) if quote else None,
        "chunk_id": normalize_whitespace(risk.get("chunk_id") or ""),
    }


def _normalize_key_term(term: dict[str, Any]) -> dict[str, Any]:
    title = normalize_whitespace(term.get("title") or "Ключевое условие") or "Ключевое условие"
    value = normalize_whitespace(term.get("value") or "")
    explanation = normalize_whitespace(term.get("explanation") or "")
    quote = normalize_quote(term.get("quote"), max_chars=420, max_sentences=3)
    if not value and quote:
        value = normalize_whitespace(quote[:180])
    if not value:
        value = "Не указано"
    return {
        "title": title,
        "value": value,
        "explanation": explanation,
        "quote": quote,
        "page": normalize_page(term.get("page")) if quote else None,
        "chunk_id": normalize_whitespace(term.get("chunk_id") or ""),
    }


def _normalize_legal_source(source: dict[str, Any]) -> dict[str, Any] | None:
    url = canonicalize_url(source.get("url"))
    if not url:
        return None
    source_type = classify_source_type_from_url(url)
    title = _humanize_source_title(str(source.get("title") or ""), source_type, url)
    snippet = normalize_whitespace(source.get("snippet") or "")
    reason = normalize_whitespace(source.get("reason") or "")
    if snippet.lower() in _MACHINE_SOURCE_LABELS:
        snippet = ""
    relevance = _normalize_relevance(source.get("relevance"))
    trust_tier = normalize_whitespace(source.get("trust_tier") or "grounded").lower()
    if trust_tier not in {"grounded", "model_reported"}:
        trust_tier = "grounded"
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "reason": reason,
        "source_type": source_type,
        "relevance": relevance,
        "trust_tier": trust_tier,
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


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for warning in warnings:
        normalized = normalize_whitespace(warning)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


class ReportAgent:
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = dict(payload or {})
        raw_warnings = report.get("warnings", [])
        if isinstance(raw_warnings, list):
            warnings = _dedupe_warnings(
                [
                    _normalize_warning_text(item)
                    for item in raw_warnings
                    if _normalize_warning_text(item)
                ]
            )
        else:
            warnings = ["Анализ выполнен, но часть данных отчета потребовала нормализации."]

        raw_risks = report.get("risks", [])
        if not isinstance(raw_risks, list):
            warnings.append("Анализ выполнен, но часть данных отчета потребовала нормализации.")
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
                str(risk.get("chunk_id", "")).strip().lower(),
            ),
        )

        raw_terms = report.get("key_terms", [])
        if not isinstance(raw_terms, list):
            warnings.append("Анализ выполнен, но часть данных отчета потребовала нормализации.")
            raw_terms = []
        normalized_terms = [_normalize_key_term(item) for item in raw_terms if isinstance(item, dict)]
        normalized_terms = _dedupe(
            normalized_terms,
            lambda term: (
                str(term.get("title", "")).strip().lower(),
                str(term.get("value", "")).strip().lower(),
                str(term.get("explanation", "")).strip().lower(),
                str(term.get("quote", "")).strip().lower(),
                str(term.get("page", "")),
                str(term.get("chunk_id", "")).strip().lower(),
            ),
        )

        raw_sources = report.get("legal_sources", [])
        if not isinstance(raw_sources, list):
            warnings.append("Анализ выполнен, но часть данных отчета потребовала нормализации.")
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
                canonicalize_url(source.get("url")),
                "",
                "",
            )
            if canonicalize_url(source.get("url"))
            else (
                "",
                str(source.get("title", "")).strip().lower(),
                str(source.get("source_type", "")).strip().lower(),
            ),
        )

        normalized_report = {
            "document_id": str(report.get("document_id", "")).strip(),
            "status": str(report.get("status", "done")).strip().lower(),
            "summary": normalize_whitespace(report.get("summary", "")),
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
                "Анализ выполнен, но часть служебных данных отчета отсутствует."
            )

        if normalized_report["status"] == "done_with_warnings":
            normalized_report["warnings"] = _dedupe_warnings(normalized_report["warnings"])
            normalized_report["warnings"] = _dedupe_warnings(normalized_report["warnings"])

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
                + ["Анализ выполнен, но итоговый отчет был собран в упрощенном режиме."],
                "disclaimer": DISCLAIMER,
                "used_ocr": bool(normalized_report.get("used_ocr", False)),
                "chunks_count": int(normalized_report.get("chunks_count", 0)),
            }
            validated_fallback = ContractReport.model_validate(fallback)
            return validated_fallback.model_dump(mode="json")


