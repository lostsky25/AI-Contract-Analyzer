from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlunparse

_SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…](?=\s|$)")
_SPACE_RE = re.compile(r"\s+")


def normalize_whitespace(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def normalize_page(value: Any) -> int | None:
    if value is None:
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def normalize_quote(
    quote: Any,
    *,
    max_chars: int = 420,
    max_sentences: int = 3,
) -> str:
    text = normalize_whitespace(quote).strip(" \"'“”«»")
    if not text:
        return ""

    sentences = [sentence.strip() for sentence in _SENTENCE_RE.findall(text) if sentence.strip()]
    if sentences:
        selected: list[str] = []
        for sentence in sentences:
            candidate = " ".join(selected + [sentence]).strip()
            if len(selected) >= max_sentences:
                break
            if len(candidate) > max_chars:
                break
            selected.append(sentence)
        if selected:
            return " ".join(selected).strip()

    shortened = text if len(text) <= max_chars else text[:max_chars].rstrip()
    if shortened and shortened[-1].isalnum():
        boundary_indexes = [shortened.rfind(ch) for ch in (".", "!", "?", ";", ":")]
        boundary = max(boundary_indexes)
        if boundary > 0:
            shortened = shortened[: boundary + 1].rstrip()
        else:
            last_space = shortened.rfind(" ")
            if last_space > 0:
                shortened = shortened[:last_space].rstrip()

    if shortened and shortened[-1].isalnum():
        words = shortened.split()
        if len(words) > 1 and len(words[-1]) <= 4:
            shortened = " ".join(words[:-1]).rstrip(",;:- ")

    return normalize_whitespace(shortened)


def classify_source_type_from_url(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    if "consultant.ru" in host:
        return "consultant_plus"
    if "garant.ru" in host:
        return "garant"
    if "pravo.gov.ru" in host:
        return "pravo_gov"
    return "other_public_source"


def canonicalize_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.netloc:
        return raw

    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            (parsed.scheme or "https").lower(),
            parsed.netloc.lower(),
            path,
            "",
            parsed.query,
            "",
        )
    )
