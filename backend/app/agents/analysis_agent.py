from app.services.chunking_service import chunk_text
from app.services.llm_service import analyze_contract
from app.services.rag_service import save_chunks, semantic_retrieval
<<<<<<< HEAD
=======
from app.config import settings
>>>>>>> feature/backend-mvp

RISK_QUERY = (
    "contract risks, obligations, penalties, payment terms, termination conditions"
)
KEY_TERMS_QUERY = (
    "key terms: duration, payment terms, liability, termination, confidentiality"
)


class AnalysisAgent:
    def retrieve_evidence(self, document_id: str, text: str) -> list[dict]:
        chunks = chunk_text(text)
        if not chunks:
            return []

        save_chunks(document_id, chunks)
        evidence = semantic_retrieval(query=RISK_QUERY, document_id=document_id, top_k=5)
        key_terms_evidence = semantic_retrieval(
            query=KEY_TERMS_QUERY,
            document_id=document_id,
            top_k=5,
        )
        merged = evidence + key_terms_evidence
        if merged:
            return merged
        return [{"text": chunk, "score": 0.0, "metadata": {"chunk_index": idx}} for idx, chunk in enumerate(chunks[:5])]

    def analyze_risks(self, evidence: list[dict]) -> dict:
        context = "\n\n".join([str(item.get("text", "")) for item in evidence if item.get("text")])
<<<<<<< HEAD
        return analyze_contract(context=context)

    def extract_key_terms(self, evidence: list[dict]) -> list[dict]:
        terms: list[dict] = []
        for item in evidence[:5]:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            snippet = text[:200]
            terms.append(
                {
                    "title": "Key clause",
                    "value": snippet,
                    "quote": snippet,
                    "page": item.get("metadata", {}).get("page"),
                }
            )
=======
        return analyze_contract(context=context, model=settings.openrouter_model_risk)

    def extract_key_terms(self, evidence: list[dict]) -> list[dict]:
        context = "\n\n".join([str(item.get("text", "")) for item in evidence if item.get("text")])
        result = analyze_contract(context=context, model=settings.openrouter_model_key_terms)
        terms: list[dict] = []
        for idx, risk_like_item in enumerate(list(result.get("risks", []))[:5], start=1):
            title = str(risk_like_item.get("type", f"Term {idx}")).strip() or f"Term {idx}"
            value = str(risk_like_item.get("description", "")).strip()
            if not value:
                continue
            terms.append({"title": title, "value": value[:200], "quote": value[:200], "page": None})
>>>>>>> feature/backend-mvp
        return terms

    def assemble_report(self, document_id: str, risk_output: dict, key_terms: list[dict], used_ocr: bool, chunks_count: int) -> dict:
        risks = list(risk_output.get("risks", []))
        severities = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        overall = "low"
        for risk in risks:
            severity = str(risk.get("severity", "low")).lower()
            if severities.get(severity, 1) > severities.get(overall, 1):
                overall = severity

        return {
            "document_id": document_id,
            "status": "done",
            "summary": str(risk_output.get("summary", "")),
            "overall_risk": overall,
            "risks": risks,
            "key_terms": key_terms,
<<<<<<< HEAD
            "disclaimer": "Система не заменяет профессионального юриста.",
=======
            "legal_sources": [],
            "warnings": [],
            "disclaimer": "Система выполняет предварительный анализ и не заменяет профессионального юриста.",
>>>>>>> feature/backend-mvp
            "used_ocr": used_ocr,
            "chunks_count": chunks_count,
        }
