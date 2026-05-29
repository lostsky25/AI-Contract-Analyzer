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


class RetrievalAgent:
    def run(
        self,
        document_id: str,
        text: str,
        chunk_records: list[dict] | None = None,
        pages: list[dict] | None = None,
    ) -> dict:
        if chunk_records:
            save_chunk_records(document_id, chunk_records)
            count = len(chunk_records)
        elif pages:
            records = chunk_records_from_pages(pages)
            for index, record in enumerate(records):
                record["chunk_id"] = f"{document_id}_{index}"
            save_chunk_records(document_id, records)
            count = len(records)
        else:
            chunks = chunk_text(text)
            save_chunks(document_id, chunks)
            count = len(chunks)

        risk_context, terms_context = batch_semantic_retrieval(
            queries=[RISK_QUERY, KEY_TERMS_QUERY],
            document_id=document_id,
            top_k=RETRIEVAL_TOP_K,
        )
        # qa_context не используется в orchestrator analyze; не вызываем лишний retrieval
        qa_context: list[dict] = []
        return {
            "chunks_count": count,
            "risk_context": risk_context,
            "terms_context": terms_context,
            "qa_context": qa_context,
        }
