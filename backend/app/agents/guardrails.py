from __future__ import annotations

import re
from typing import Any

MAX_QUESTION_LENGTH = 1200

OFFTOPIC_REFUSAL = (
    "Я могу отвечать только на вопросы по загруженному договору. "
    "Задайте вопрос о рисках, условиях, оплате, ответственности, сроках или расторжении."
)
INJECTION_REFUSAL = (
    "Я не могу выполнять инструкции, которые не относятся к анализу загруженного договора. "
    "Могу ответить только на вопросы по содержанию документа."
)
UNGROUNDED_ANSWER = "В загруженном документе не найдено достаточно подтвержденной информации для ответа."

_CONTRACT_KEYWORDS = (
    "документ",
    "договор",
    "контракт",
    "оферт",
    "приложен",
    "тариф",
    "соглашен",
    "сторон",
    "исполнител",
    "заказчик",
    "оплат",
    "срок",
    "штраф",
    "пен",
    "ответствен",
    "расторжен",
    "права",
    "обязан",
    "услуг",
    "товар",
    "предмет",
    "услов",
    "риск",
    "цитат",
    "страниц",
    "пункт",
    "раздел",
    "в документе",
    "в тексте",
    "в договоре",
    "юрист",
    "согласов",
)

_SHORT_ALLOWED_QUESTIONS = (
    "какие риски",
    "какие штрафы",
    "кто стороны",
    "какие сроки",
    "какая оплата",
    "какие обязанности",
    "какая ответственность",
    "какие пункты требуют согласования с юристом",
    "что самое рискованное",
)

_OFFTOPIC_HINTS = (
    "напиши код",
    "создай программу",
    "сортировк",
    "пузырьк",
    "python",
    "javascript",
    "java ",
    "рецепт",
    "приготов",
    "анекдот",
    "политик",
    "истори",
    "математ",
    "реши задач",
    "что такое gpt",
    "переведи текст",
    "сделай сайт",
)

_GENERATION_VERBS = (
    "напиши",
    "создай",
    "сделай",
    "покажи",
    "расскажи",
    "write",
    "build",
)

_PROMPT_INJECTION_PATTERNS = (
    r"\bignore\s+previous\s+instructions?\b",
    r"\bdisregard\s+previous\s+instructions?\b",
    r"\bsystem\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\breveal\s+hidden\s+prompt\b",
    r"\bjailbreak\b",
    r"\bbypass\b",
    r"\bforget\s+(all\s+)?(previous|earlier)\s+instructions?\b",
    r"забуд[ьт]\s+инструкц",
    r"игнорируй(\s+\w+){0,3}\s+инструкц",
    r"игнорируй(\s+\w+){0,3}\s+правил",
    r"ответ(ь|ьте)?\s+на\s+любой\s+вопрос",
    r"выведи\s+системн(ый|ого)\s+промпт",
    r"следуй\s+только\s+моим\s+инструкц",
    r"не\s+используй\s+договор",
    r"ответ(ь|ьте)?\s+не\s+по\s+документ",
    r"\bprint\s+the\s+system\s+prompt\b",
)

_HARMFUL_REQUEST_PATTERNS = (
    r"(как|how)\s+взлома",
    r"(как|how)\s+(сделать|выполнить)\s+(sql[\s\-]?injection|sql[\s\-]?инъекц)",
)

_NO_INFO_MARKERS = (
    "не найдено достаточно информации",
    "недостаточно информации",
    "недостаточно данных",
    "insufficient information",
    "not enough information",
)


def normalize_user_question(question: str) -> str:
    collapsed = re.sub(r"\s+", " ", question or "").strip()
    if not collapsed:
        raise ValueError("Question must not be empty.")
    return collapsed[:MAX_QUESTION_LENGTH]


def _looks_like_explicit_offtopic_generation(normalized: str) -> bool:
    has_verb = any(verb in normalized for verb in _GENERATION_VERBS)
    has_offtopic = any(hint in normalized for hint in _OFFTOPIC_HINTS)
    return has_verb and has_offtopic


def detect_prompt_injection(text: str) -> bool:
    normalized = normalize_user_question(text).lower()

    for pattern in _PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return True

    for pattern in _HARMFUL_REQUEST_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return False


def is_contract_question(question: str) -> bool:
    normalized = normalize_user_question(question).lower()

    if _looks_like_explicit_offtopic_generation(normalized):
        return False

    if any(short_hint in normalized for short_hint in _SHORT_ALLOWED_QUESTIONS):
        return True

    # Relaxed document-anchor detection for Q&A usability:
    # accept if the user clearly references the uploaded document context.
    if "документ" in normalized and any(h in normalized for h in ("тариф", "оферт", "приложен", "услов")):
        return True

    mentions_contract = any(keyword in normalized for keyword in _CONTRACT_KEYWORDS)
    off_topic = any(hint in normalized for hint in _OFFTOPIC_HINTS)

    if mentions_contract:
        return True

    if off_topic:
        return False

    return False


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _alnum_tokens(value: str) -> list[str]:
    return re.findall(r"[a-zа-я0-9]+", value.lower())


def _quote_overlaps_evidence(quote: str, evidence_text: str) -> bool:
    quote_norm = _normalize_text(quote)
    evidence_norm = _normalize_text(evidence_text)
    if not quote_norm or not evidence_norm:
        return False
    if quote_norm in evidence_norm:
        return True

    quote_tokens = _alnum_tokens(quote_norm)
    if len(quote_tokens) < 3:
        return False
    evidence_tokens = set(_alnum_tokens(evidence_norm))
    overlap_count = sum(1 for token in quote_tokens if token in evidence_tokens)
    return (overlap_count / max(len(quote_tokens), 1)) >= 0.6


def _citation_field(citation: Any, field: str, default: Any = None) -> Any:
    if isinstance(citation, dict):
        return citation.get(field, default)
    return getattr(citation, field, default)


def _is_no_info_answer(answer: str) -> bool:
    normalized = _normalize_text(answer)
    return any(marker in normalized for marker in _NO_INFO_MARKERS)


def validate_answer_grounding(
    answer: str,
    citations: list[Any],
    evidence_chunks: list[dict[str, Any]],
) -> bool:
    if _is_no_info_answer(answer):
        return True
    if not answer.strip() or not citations:
        return False

    evidence_by_chunk_id: dict[str, dict[str, Any]] = {}
    evidence_by_page: dict[int, list[dict[str, Any]]] = {}
    for item in evidence_chunks:
        chunk_id = str(item.get("chunk_id", "")).strip()
        page = item.get("page")
        if chunk_id:
            evidence_by_chunk_id[chunk_id] = item
        if isinstance(page, int):
            evidence_by_page.setdefault(page, []).append(item)

    for citation in citations:
        quote = str(_citation_field(citation, "quote", "")).strip()
        chunk_id = str(_citation_field(citation, "chunk_id", "")).strip()
        page = _citation_field(citation, "page", None)
        if not quote:
            return False

        matched_evidence: list[dict[str, Any]] = []
        if chunk_id:
            matched = evidence_by_chunk_id.get(chunk_id)
            if not matched:
                return False
            matched_evidence = [matched]
            if isinstance(page, int) and matched.get("page") != page:
                return False
        elif isinstance(page, int):
            matched_evidence = evidence_by_page.get(page, [])
            if not matched_evidence:
                return False
        else:
            return False

        if not any(
            _quote_overlaps_evidence(quote, str(item.get("text", "")))
            for item in matched_evidence
        ):
            return False

    return True


def safe_offtopic_answer() -> str:
    return OFFTOPIC_REFUSAL


def safe_injection_answer() -> str:
    return INJECTION_REFUSAL
