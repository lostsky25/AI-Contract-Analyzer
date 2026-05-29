from app.services.chunking_service import chunk_records_from_pages, chunk_text
from app.services.rag_service import save_chunk_records, save_chunks, semantic_retrieval

RISK_QUERY = (
    "contract risks, obligations, penalties, payment terms, termination conditions"
)
KEY_TERMS_QUERY = (
    "key terms: duration, payment terms, liability, termination, confidentiality"
)
QA_QUERY = "question answering over contract clauses and obligations"


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

        risk_context = semantic_retrieval(query=RISK_QUERY, document_id=document_id, top_k=5)
        terms_context = semantic_retrieval(
            query=KEY_TERMS_QUERY,
            document_id=document_id,
            top_k=5,
        )
        qa_context = semantic_retrieval(query=QA_QUERY, document_id=document_id, top_k=5)
        return {
            "chunks_count": count,
            "risk_context": risk_context,
            "terms_context": terms_context,
            "qa_context": qa_context,
        }
