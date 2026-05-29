from __future__ import annotations

from typing import Any

from app.models.schemas import OrchestrateResponse

LEGAL_SOURCE_TYPES = {
    "consultant_plus",
    "garant",
    "pravo_gov",
    "other_public_source",
}
LEGAL_RELEVANCE = {"low", "medium", "high", "unknown"}
REPORT_STATUSES = {"processing", "done", "failed", "done_with_warnings"}
OVERALL_RISK = {"low", "medium", "high", "unknown", "critical"}


def validate_report_schema(payload: dict[str, Any]) -> list[str]:
    """Return a list of validation error messages (empty if valid)."""
    errors: list[str] = []

    try:
        OrchestrateResponse.model_validate(payload)
    except Exception as exc:
        errors.append(f"OrchestrateResponse validation failed: {exc}")
        return errors

    status = str(payload.get("status", ""))
    if status not in REPORT_STATUSES:
        errors.append(f"Invalid status: {status}")

    overall = str(payload.get("overall_risk", "")).lower()
    if overall not in OVERALL_RISK:
        errors.append(f"Invalid overall_risk: {overall}")

    if not str(payload.get("summary", "")).strip():
        errors.append("summary must be non-empty")

    if not str(payload.get("disclaimer", "")).strip():
        errors.append("disclaimer must be non-empty")

    if not isinstance(payload.get("risks"), list):
        errors.append("risks must be a list")
    if not isinstance(payload.get("key_terms"), list):
        errors.append("key_terms must be a list")
    if not isinstance(payload.get("legal_sources"), list):
        errors.append("legal_sources must be a list")

    for index, risk in enumerate(payload.get("risks", [])):
        if not isinstance(risk, dict):
            errors.append(f"risks[{index}] must be an object")
            continue
        if not str(risk.get("title", "")).strip():
            errors.append(f"risks[{index}].title is required")
        if not isinstance(risk.get("quote", ""), str):
            errors.append(f"risks[{index}].quote must be a string")

    for index, term in enumerate(payload.get("key_terms", [])):
        if not isinstance(term, dict):
            errors.append(f"key_terms[{index}] must be an object")
            continue
        if not str(term.get("title", "")).strip():
            errors.append(f"key_terms[{index}].title is required")

    for index, source in enumerate(payload.get("legal_sources", [])):
        if not isinstance(source, dict):
            errors.append(f"legal_sources[{index}] must be an object")
            continue
        source_type = str(source.get("source_type", ""))
        if source_type not in LEGAL_SOURCE_TYPES:
            errors.append(f"legal_sources[{index}].source_type invalid: {source_type}")
        relevance = str(source.get("relevance", "unknown"))
        if relevance not in LEGAL_RELEVANCE:
            errors.append(f"legal_sources[{index}].relevance invalid: {relevance}")

    return errors


def validate_legal_sources_state(report: dict[str, Any]) -> list[str]:
    """legal_sources must be a list; empty list requires warnings (non-fatal)."""
    errors: list[str] = []
    sources = report.get("legal_sources")
    warnings = report.get("warnings")

    if not isinstance(sources, list):
        return ["legal_sources must be a list"]

    if sources:
        for index, source in enumerate(sources):
            if not str(source.get("url", "")).strip():
                errors.append(f"legal_sources[{index}].url is required")
    elif not warnings:
        errors.append("empty legal_sources requires non-empty warnings")

    return errors
