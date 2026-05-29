from app.config import settings
from app.services.llm_service import analyze_contract

RISK_QUERY = (
    "contract risks, obligations, penalties, payment terms, termination conditions"
)
KEY_TERMS_QUERY = (
    "key terms: duration, payment terms, liability, termination, confidentiality"
)


def _format_evidence_context(evidence: list[dict]) -> str:
    blocks: list[str] = []
    for item in evidence:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        page = item.get("page")
        chunk_id = item.get("chunk_id", "")
        page_label = str(page) if page is not None else "unknown"
        blocks.append(f"[page={page_label}][chunk_id={chunk_id}]\n{text}")
    return "\n\n---\n\n".join(blocks)


def _pick_evidence(evidence: list[dict], index: int) -> dict | None:
    if not evidence:
        return None
    return evidence[min(index, len(evidence) - 1)]


def _normalize_risk_item(item: dict, evidence: list[dict], index: int) -> dict:
    picked = _pick_evidence(evidence, index)
    title = str(item.get("title") or item.get("type") or f"Risk {index + 1}").strip()
    explanation = str(
        item.get("explanation") or item.get("description") or ""
    ).strip()
    quote = str(item.get("quote") or "").strip()
    page = item.get("page")

    if picked:
        if page is None:
            page = picked.get("page")
        if not quote:
            quote = str(picked.get("text", ""))[:500]

    if not quote and explanation:
        quote = explanation[:500]

    severity = str(item.get("severity", "unknown")).lower()

    return {
        "title": title or f"Risk {index + 1}",
        "severity": severity,
        "explanation": explanation,
        "quote": quote or "Цитата не найдена в evidence.",
        "page": page,
    }


def _normalize_key_term(item: dict, evidence: list[dict], index: int) -> dict:
    picked = _pick_evidence(evidence, index)
    title = str(item.get("title") or item.get("type") or f"Term {index + 1}").strip()
    value = str(item.get("value") or item.get("description") or "").strip()
    quote = str(item.get("quote") or "").strip()
    page = item.get("page")

    if picked:
        if page is None:
            page = picked.get("page")
        if not quote:
            quote = str(picked.get("text", ""))[:500]

    if not value and quote:
        value = quote[:200]

    return {
        "title": title or f"Term {index + 1}",
        "value": value or "Не указано",
        "quote": quote or value[:200] or "Цитата не найдена в evidence.",
        "page": page,
    }


class AnalysisAgent:
    def analyze_risks(self, evidence: list[dict]) -> dict:
        context = _format_evidence_context(evidence)
        result = analyze_contract(context=context, model=settings.openrouter_model_risk)
        raw_risks = list(result.get("risks", []))
        result["risks"] = [
            _normalize_risk_item(risk, evidence, index) for index, risk in enumerate(raw_risks)
        ]
        return result

    def extract_key_terms(self, evidence: list[dict]) -> list[dict]:
        context = _format_evidence_context(evidence)
        result = analyze_contract(
            context=context, model=settings.openrouter_model_key_terms
        )
        terms: list[dict] = []
        for index, risk_like_item in enumerate(list(result.get("risks", []))[:5], start=0):
            value = str(risk_like_item.get("description", "")).strip()
            if not value and not risk_like_item.get("type"):
                continue
            terms.append(
                _normalize_key_term(
                    {
                        "title": risk_like_item.get("type"),
                        "value": value,
                        "description": value,
                    },
                    evidence,
                    index,
                )
            )
        return terms

    def assemble_report(
        self,
        document_id: str,
        risk_output: dict,
        key_terms: list[dict],
        used_ocr: bool,
        chunks_count: int,
    ) -> dict:
        risks = list(risk_output.get("risks", []))
        severities = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 0}
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
            "legal_sources": [],
            "warnings": [],
            "disclaimer": (
                "Система выполняет предварительный анализ и не заменяет "
                "профессионального юриста."
            ),
            "used_ocr": used_ocr,
            "chunks_count": chunks_count,
        }
