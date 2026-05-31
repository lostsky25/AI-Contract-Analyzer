import logging

from app.services.chunking_service import chunk_records_from_pages, chunk_text
from app.services.rag_service import (
    batch_semantic_retrieval,
    save_chunk_records,
    save_chunks,
)

RISK_QUERY = (
    "риски договора обязательства штрафы неустойка срок оплаты расторжение"
)
KEY_TERMS_QUERY = (
    "ключевые условия срок действия оплата ответственность расторжение конфиденциальность"
)

RETRIEVAL_TOP_K = 4
FALLBACK_MAX_CHUNKS = 6
FALLBACK_HEAD_CHUNKS = 2
FALLBACK_RISK_KEYWORDS = (
    "риск",
    "штраф",
    "неустойк",
    "ответственн",
    "убыт",
    "liability",
    "penalt",
    "breach",
)
FALLBACK_TERMS_KEYWORDS = (
    "оплат",
    "цена",
    "срок",
    "расторж",
    "конфиденц",
    "payment",
    "term",
    "termination",
    "confidential",
)
INDEX_UNAVAILABLE_WARNING = (
    "Текст договора был извлечён, но не удалось построить поисковый индекс для анализа."
)
INDEX_UNAVAILABLE_FALLBACK_WARNING = (
    "Поисковый индекс был недоступен, анализ выполнен по извлечённым фрагментам договора."
)
logger = logging.getLogger(__name__)


def _score_record(record: dict, keywords: tuple[str, ...]) -> int:
    text = str(record.get("text", "")).lower()
    score = 0
    for keyword in keywords:
        if keyword in text:
            score += 1
    return score


def _fallback_subset(
    records: list[dict],
    *,
    keywords: tuple[str, ...],
    max_chunks: int = FALLBACK_MAX_CHUNKS,
) -> list[dict]:
    normalized: list[dict] = []
    for index, record in enumerate(records):
        text = str(record.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "text": text,
                "page": record.get("page"),
                "chunk_id": str(record.get("chunk_id") or f"fallback_{index}"),
                "chunk_index": int(record.get("chunk_index", index)),
            }
        )
    if not normalized:
        return []

    head = normalized[:FALLBACK_HEAD_CHUNKS]
    ranked = sorted(
        normalized,
        key=lambda item: (-_score_record(item, keywords), int(item.get("chunk_index", 0))),
    )
    selected_ids: set[str] = set()
    selected: list[dict] = []
    for item in head + ranked:
        chunk_id = str(item.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id in selected_ids:
            continue
        selected_ids.add(chunk_id)
        selected.append(item)
        if len(selected) >= max_chunks:
            break
    return selected


class RetrievalAgent:
    def run(
        self,
        document_id: str,
        text: str,
        chunk_records: list[dict] | None = None,
        pages: list[dict] | None = None,
    ) -> dict:
        warnings: list[str] = []
        retrieval_warning_reason = ""

        if chunk_records:
            records = list(chunk_records)
            for index, record in enumerate(records):
                record["chunk_id"] = str(record.get("chunk_id") or f"{document_id}_{index}")
                record["chunk_index"] = int(record.get("chunk_index", index))
        elif pages:
            records = chunk_records_from_pages(pages)
            for index, record in enumerate(records):
                record["chunk_id"] = f"{document_id}_{index}"
                record["chunk_index"] = int(record.get("chunk_index", index))
        else:
            chunks = chunk_text(text)
            records = [
                {
                    "text": chunk,
                    "page": None,
                    "chunk_id": f"{document_id}_{index}",
                    "chunk_index": index,
                }
                for index, chunk in enumerate(chunks)
            ]
        count = len(records)

        indexed_chunks_count = 0
        try:
            if chunk_records or pages:
                indexed_chunks_count = save_chunk_records(document_id, records)
            else:
                indexed_chunks_count = save_chunks(document_id, [record["text"] for record in records])
        except Exception as exc:
            retrieval_warning_reason = str(exc) or "indexing_failed"
            warnings.append(INDEX_UNAVAILABLE_WARNING)
            logger.warning(
                "retrieval_index_unavailable doc=%s chunks_to_save=%d reason=%s",
                document_id[:8],
                count,
                retrieval_warning_reason,
            )

        risk_context: list[dict] = []
        terms_context: list[dict] = []
        if not warnings:
            try:
                risk_context, terms_context = batch_semantic_retrieval(
                    queries=[RISK_QUERY, KEY_TERMS_QUERY],
                    document_id=document_id,
                    top_k=RETRIEVAL_TOP_K,
                )
            except Exception as exc:
                retrieval_warning_reason = str(exc) or "retrieval_failed"
                warnings.append(INDEX_UNAVAILABLE_WARNING)
                logger.warning(
                    "retrieval_query_failed doc=%s query_count=%d reason=%s",
                    document_id[:8],
                    2,
                    retrieval_warning_reason,
                )

        retrieval_fully_empty = not risk_context and not terms_context
        if (warnings or retrieval_fully_empty) and count > 0:
            if INDEX_UNAVAILABLE_FALLBACK_WARNING not in warnings:
                warnings.append(INDEX_UNAVAILABLE_FALLBACK_WARNING)
            risk_context = risk_context or _fallback_subset(records, keywords=FALLBACK_RISK_KEYWORDS)
            terms_context = terms_context or _fallback_subset(records, keywords=FALLBACK_TERMS_KEYWORDS)
            logger.info(
                "retrieval_fallback_used doc=%s fallback_risk_chunks=%d fallback_terms_chunks=%d",
                document_id[:8],
                len(risk_context),
                len(terms_context),
            )
        elif count > 0 and (not risk_context or not terms_context):
            risk_context = risk_context or _fallback_subset(records, keywords=FALLBACK_RISK_KEYWORDS)
            terms_context = terms_context or _fallback_subset(records, keywords=FALLBACK_TERMS_KEYWORDS)

        if not warnings and count > 0 and not risk_context and not terms_context:
            warnings.append(INDEX_UNAVAILABLE_WARNING)
            logger.warning(
                "retrieval_empty_context doc=%s chunks_count=%d reason=no_results",
                document_id[:8],
                count,
            )

        return {
            "chunks_count": count,
            "indexed_chunks_count": indexed_chunks_count,
            "risk_context": risk_context,
            "terms_context": terms_context,
            "qa_context": [],
            "warnings": warnings,
            "retrieval_diagnostics": {
                "retrieval_query_count": 2,
                "retrieved_chunks_count": len(risk_context) + len(terms_context),
                "document_filter_used": True,
                "retrieval_empty_reason": retrieval_warning_reason,
            },
        }
