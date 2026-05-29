from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.llm_service import ask_llm_json
from app.services.rag_service import semantic_retrieval

logger = logging.getLogger(__name__)

QA_DISCLAIMER = (
    "Ответ сформирован только на основе текста загруженного договора "
    "и не является юридической консультацией."
)
NO_INFO_ANSWER = (
    "В загруженном документе не найдено достаточно информации для ответа."
)
SAFE_FALLBACK_ANSWER = (
    "Не удалось сформировать ответ. Попробуйте переформулировать вопрос."
)

ConfidenceLevel = Literal["low", "medium", "high", "unknown"]


class QACitation(BaseModel):
    quote: str
    page: int | None = None
    chunk_id: str = ""


class QALLMResponse(BaseModel):
    answer: str
    confidence: ConfidenceLevel = "unknown"
    citations: list[QACitation] = Field(default_factory=list)


SYSTEM_PROMPT = """Ты отвечаешь на вопросы по загруженному договору, используя ТОЛЬКО приведённые фрагменты (evidence).
Правила:
- Отвечай строго по evidence; не выдумывай факты.
- Не ссылайся на законы и внешние базы, если их нет в evidence.
- Не давай юридических консультаций.
- Если данных недостаточно — явно укажи это и поставь confidence: low.
- Поле answer и цитаты — только на русском языке.
- Верни только валидный JSON.
"""


def _resolve_chunk_id(item: dict[str, Any], document_id: str) -> str:
    if item.get("chunk_id"):
        return str(item["chunk_id"])
    metadata = item.get("metadata") or {}
    if "chunk_id" in metadata:
        return str(metadata["chunk_id"])
    if "chunk_index" in metadata:
        return f"{document_id}_{metadata['chunk_index']}"
    return ""


def _resolve_page(item: dict[str, Any]) -> int | None:
    if "page" in item:
        page = item.get("page")
        return int(page) if isinstance(page, int) else None
    metadata = item.get("metadata") or {}
    page = metadata.get("page")
    if page is None:
        return None
    try:
        page_int = int(page)
    except (TypeError, ValueError):
        return None
    return None if page_int <= 0 else page_int


def _format_evidence(chunks: list[dict[str, Any]], document_id: str) -> str:
    blocks: list[str] = []
    for item in chunks:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        chunk_id = _resolve_chunk_id(item, document_id)
        page = _resolve_page(item)
        page_str = str(page) if page is not None else "unknown"
        blocks.append(f"[chunk_id={chunk_id}; page={page_str}]\n{text}")
    return "\n\n---\n\n".join(blocks)


def _build_user_prompt(question: str, evidence: str) -> str:
    return f"""Вопрос:
{question}

Фрагменты договора (evidence):
{evidence}

Верни JSON (answer на русском):
{{
  "answer": "ответ на русском",
  "confidence": "low | medium | high | unknown",
  "citations": [
    {{
      "quote": "точная цитата из evidence",
      "page": 1,
      "chunk_id": "document_chunk_id"
    }}
  ]
}}
"""


def _citations_from_chunks(chunks: list[dict[str, Any]], document_id: str) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in chunks[:3]:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        citations.append(
            {
                "quote": text[:500],
                "page": _resolve_page(item),
                "chunk_id": _resolve_chunk_id(item, document_id),
            }
        )
    return citations


class DocumentQAAgent:
    top_k: int = 5

    def run(self, document_id: str, question: str) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Question must not be empty.")

        try:
            chunks = semantic_retrieval(
                query=normalized_question,
                document_id=document_id,
                top_k=self.top_k,
            )
        except Exception as exc:
            logger.warning("Q&A retrieval failed for %s: %s", document_id, exc)
            chunks = []

        has_text = any(str(item.get("text", "")).strip() for item in chunks)
        if not has_text:
            return {
                "document_id": document_id,
                "question": normalized_question,
                "answer": NO_INFO_ANSWER,
                "confidence": "low",
                "citations": [],
                "disclaimer": QA_DISCLAIMER,
            }

        evidence = _format_evidence(chunks, document_id)
        try:
            if not settings.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is missing.")
            parsed_raw = ask_llm_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=_build_user_prompt(normalized_question, evidence),
                model=settings.openrouter_model_qa,
            )
            parsed = QALLMResponse.model_validate(parsed_raw)
        except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning("Q&A LLM failed for %s: %s", document_id, exc)
            return {
                "document_id": document_id,
                "question": normalized_question,
                "answer": SAFE_FALLBACK_ANSWER,
                "confidence": "low",
                "citations": _citations_from_chunks(chunks, document_id),
                "disclaimer": QA_DISCLAIMER,
            }

        citations = [
            {
                "quote": c.quote.strip(),
                "page": c.page,
                "chunk_id": c.chunk_id.strip(),
            }
            for c in parsed.citations
            if c.quote.strip()
        ]
        if not citations:
            citations = _citations_from_chunks(chunks, document_id)

        answer = parsed.answer.strip() or NO_INFO_ANSWER
        confidence = parsed.confidence if answer != NO_INFO_ANSWER else "low"

        return {
            "document_id": document_id,
            "question": normalized_question,
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "disclaimer": QA_DISCLAIMER,
        }
