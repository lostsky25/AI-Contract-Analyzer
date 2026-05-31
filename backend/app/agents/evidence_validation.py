from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.agents.normalization_utils import normalize_page, normalize_quote, normalize_whitespace

SEVERITY_VALUES = {"low", "medium", "high", "unknown"}

_URL_RE = re.compile(r"^(?:https?://|www\.)", flags=re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+", flags=re.UNICODE)
_SPACE_RE = re.compile(r"\s+")

_TRANSLATION_MAP = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "‑": "-",
    }
)


@dataclass
class GroundingValidationResult:
    accepted: list[dict[str, Any]]
    reject_counts: dict[str, int]
    normalized_severity_count: int = 0


def _empty_reject_counts() -> dict[str, int]:
    return {
        "missing_title": 0,
        "missing_explanation": 0,
        "missing_value": 0,
        "missing_quote": 0,
        "missing_page_or_chunk": 0,
        "quote_not_found": 0,
        "quote_is_url": 0,
        "invalid_severity": 0,
    }


def _normalize_for_matching(value: Any) -> str:
    text = str(value or "").translate(_TRANSLATION_MAP).lower()
    text = _SPACE_RE.sub(" ", text)
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(value)


def _is_url_like(value: str) -> bool:
    return bool(_URL_RE.match(str(value or "").strip()))


def _quote_matches_evidence(quote: str, evidence_text: str) -> bool:
    quote_norm = _normalize_for_matching(quote)
    evidence_norm = _normalize_for_matching(evidence_text)
    if not quote_norm or not evidence_norm:
        return False

    if quote_norm in evidence_norm:
        return True

    quote_tokens = _tokens(quote_norm)
    if len(quote_tokens) < 4:
        return False

    evidence_tokens = set(_tokens(evidence_norm))
    overlap = sum(1 for token in quote_tokens if token in evidence_tokens)
    overlap_ratio = overlap / max(len(quote_tokens), 1)
    if overlap_ratio >= 0.9:
        return True

    # OCR-safe fallback: high similarity threshold.
    ratio = SequenceMatcher(None, quote_norm, evidence_norm).ratio()
    return ratio >= 0.82


def _evidence_candidates_for_quote(
    *,
    evidence: list[dict[str, Any]],
    page: int | None,
    chunk_id: str,
) -> list[dict[str, Any]]:
    if chunk_id:
        by_chunk = [item for item in evidence if str(item.get("chunk_id", "")).strip() == chunk_id]
        if by_chunk:
            return by_chunk
    if page is not None:
        by_page = [item for item in evidence if normalize_page(item.get("page")) == page]
        if by_page:
            return by_page
    return evidence


def _metadata_available(evidence: list[dict[str, Any]]) -> bool:
    for item in evidence:
        if str(item.get("chunk_id", "")).strip():
            return True
        if normalize_page(item.get("page")) is not None:
            return True
    return False


def validate_risk_grounding(
    *,
    raw_risks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> GroundingValidationResult:
    reject_counts = _empty_reject_counts()
    accepted: list[dict[str, Any]] = []
    metadata_required = _metadata_available(evidence)
    normalized_severity_count = 0

    for index, item in enumerate(raw_risks):
        title = normalize_whitespace(item.get("title") or item.get("type") or "")
        explanation = normalize_whitespace(item.get("explanation") or item.get("description") or "")
        quote = normalize_quote(item.get("quote"), max_chars=420, max_sentences=3)
        page = normalize_page(item.get("page"))
        chunk_id = str(item.get("chunk_id", "")).strip()
        severity = str(item.get("severity", "unknown")).strip().lower()

        if not title:
            reject_counts["missing_title"] += 1
            continue
        if not explanation:
            reject_counts["missing_explanation"] += 1
            continue
        if not quote:
            reject_counts["missing_quote"] += 1
            continue
        if _is_url_like(quote):
            reject_counts["quote_is_url"] += 1
            continue
        if metadata_required and page is None and not chunk_id:
            reject_counts["missing_page_or_chunk"] += 1
            continue
        if severity not in SEVERITY_VALUES:
            severity = "unknown"
            normalized_severity_count += 1
            reject_counts["invalid_severity"] += 1

        candidates = _evidence_candidates_for_quote(evidence=evidence, page=page, chunk_id=chunk_id)
        matched_item = next(
            (
                candidate
                for candidate in candidates
                if _quote_matches_evidence(quote, str(candidate.get("text", "")))
            ),
            None,
        )
        if matched_item is None:
            reject_counts["quote_not_found"] += 1
            continue

        resolved_chunk_id = chunk_id or str(matched_item.get("chunk_id", "")).strip()
        resolved_page = page if page is not None else normalize_page(matched_item.get("page"))
        if metadata_required and resolved_page is None and not resolved_chunk_id:
            reject_counts["missing_page_or_chunk"] += 1
            continue

        accepted.append(
            {
                "title": title or f"Риск {index + 1}",
                "severity": severity,
                "explanation": explanation,
                "quote": quote,
                "page": resolved_page,
                "chunk_id": resolved_chunk_id,
            }
        )

    return GroundingValidationResult(
        accepted=accepted,
        reject_counts=reject_counts,
        normalized_severity_count=normalized_severity_count,
    )


def validate_key_term_grounding(
    *,
    raw_terms: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> GroundingValidationResult:
    reject_counts = _empty_reject_counts()
    accepted: list[dict[str, Any]] = []
    metadata_required = _metadata_available(evidence)

    for index, item in enumerate(raw_terms):
        title = normalize_whitespace(item.get("title") or item.get("name") or item.get("type") or "")
        value = normalize_whitespace(item.get("value") or item.get("description") or item.get("meaning") or "")
        explanation = normalize_whitespace(item.get("explanation") or "")
        quote = normalize_quote(item.get("quote"), max_chars=420, max_sentences=3)
        page = normalize_page(item.get("page"))
        chunk_id = str(item.get("chunk_id", "")).strip()

        if not title:
            reject_counts["missing_title"] += 1
            continue
        if not value:
            reject_counts["missing_value"] += 1
            continue
        if not quote:
            reject_counts["missing_quote"] += 1
            continue
        if _is_url_like(quote):
            reject_counts["quote_is_url"] += 1
            continue
        if metadata_required and page is None and not chunk_id:
            reject_counts["missing_page_or_chunk"] += 1
            continue

        candidates = _evidence_candidates_for_quote(evidence=evidence, page=page, chunk_id=chunk_id)
        matched_item = next(
            (
                candidate
                for candidate in candidates
                if _quote_matches_evidence(quote, str(candidate.get("text", "")))
            ),
            None,
        )
        if matched_item is None:
            reject_counts["quote_not_found"] += 1
            continue

        resolved_chunk_id = chunk_id or str(matched_item.get("chunk_id", "")).strip()
        resolved_page = page if page is not None else normalize_page(matched_item.get("page"))
        if metadata_required and resolved_page is None and not resolved_chunk_id:
            reject_counts["missing_page_or_chunk"] += 1
            continue

        accepted.append(
            {
                "title": title or f"Условие {index + 1}",
                "value": value,
                "explanation": explanation,
                "quote": quote,
                "page": resolved_page,
                "chunk_id": resolved_chunk_id,
            }
        )

    return GroundingValidationResult(accepted=accepted, reject_counts=reject_counts)
