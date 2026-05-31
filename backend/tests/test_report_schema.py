import json
from pathlib import Path

from app.agents.report_agent import ReportAgent
from app.models.schemas import ContractReport, OrchestrateResponse
from helpers.report_validation import (
    validate_legal_sources_state,
    validate_report_schema,
)


def _sample_report() -> dict:
    return {
        "document_id": "doc-schema-1",
        "status": "done_with_warnings",
        "summary": "Contract has penalty and unilateral termination clauses.",
        "overall_risk": "medium",
        "risks": [
            {
                "title": "Penalty",
                "severity": "medium",
                "explanation": "Daily penalty is present.",
                "quote": "Penalty 0.1% per day",
                "page": 1,
                "chunk_id": "doc-schema-1_0",
            }
        ],
        "key_terms": [
            {
                "title": "Payment term",
                "value": "10 banking days",
                "explanation": "Payment timeline is explicit.",
                "quote": "Payment within 10 banking days",
                "page": 1,
                "chunk_id": "doc-schema-1_1",
            }
        ],
        "legal_sources": [
            {
                "title": "Civil code article",
                "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                "snippet": "Civil law obligations and liability.",
                "reason": "Relevant to penalty and liability clauses.",
                "source_type": "consultant_plus",
                "relevance": "high",
                "trust_tier": "grounded",
            }
        ],
        "warnings": ["Legal web search provider is unavailable."],
        "disclaimer": "Preliminary analysis only; not legal advice.",
        "used_ocr": False,
        "chunks_count": 2,
    }


def test_orchestrate_response_validates_sample_report() -> None:
    payload = _sample_report()
    model = OrchestrateResponse.model_validate(payload)
    assert model.document_id == "doc-schema-1"
    assert model.status == "done_with_warnings"


def test_contract_report_accepts_canonical_and_legacy_statuses() -> None:
    base = _sample_report()
    for status in ("done", "done_with_warnings", "failed", "processing", "analyzed"):
        payload = {**base, "status": status}
        model = ContractReport.model_validate(payload)
        assert model.status == status


def test_validate_report_schema_accepts_complete_payload() -> None:
    errors = validate_report_schema(_sample_report())
    assert errors == []


def test_report_schema_contains_grounded_risk_fields() -> None:
    risk = _sample_report()["risks"][0]
    assert risk["quote"]
    assert "page" in risk
    assert "chunk_id" in risk


def test_report_schema_contains_grounded_key_term_fields() -> None:
    term = _sample_report()["key_terms"][0]
    assert term["quote"]
    assert "page" in term
    assert "chunk_id" in term


def test_validate_legal_sources_empty_with_warnings() -> None:
    errors = validate_legal_sources_state(_sample_report())
    assert errors == []


def test_validate_legal_sources_empty_without_warnings_fails() -> None:
    report = _sample_report()
    report["legal_sources"] = []
    report["warnings"] = []
    errors = validate_legal_sources_state(report)
    assert any("warnings" in message for message in errors)


def test_report_agent_fallback_report() -> None:
    agent = ReportAgent()
    normalized = agent.run(
        {
            "document_id": "doc-fallback",
            "status": "done",
            "summary": "Short summary.",
            "overall_risk": "low",
            "risks": [{"title": "Risk A", "severity": "low", "explanation": "Detail."}],
            "key_terms": [{"title": "Payment", "value": "30 days"}],
            "legal_sources": [],
            "warnings": ["provider unavailable"],
        }
    )

    assert normalized["status"] == "done_with_warnings"
    assert normalized["risks"][0]["quote"] == ""
    assert normalized["key_terms"][0]["quote"] == ""
    assert normalized["disclaimer"]
    assert validate_report_schema({**normalized, "used_ocr": False, "chunks_count": 1}) == []


def test_docs_report_schema_matches_current_contract() -> None:
    docs_path = Path(__file__).resolve().parents[2] / "docs" / "report-schema.json"
    payload = json.loads(docs_path.read_text(encoding="utf-8"))

    contract_report = payload["contract_report"]
    risk = contract_report["risks"][0]
    key_term = contract_report["key_terms"][0]

    assert risk["quote"] == "string"
    assert risk["page"] == "integer | null"
    assert risk["chunk_id"] == "string"

    assert key_term["quote"] == "string"
    assert key_term["page"] == "integer | null"
    assert key_term["chunk_id"] == "string"
    assert contract_report["legal_sources"][0]["reason"] == "string"

    assert "warnings" in contract_report
    assert "used_ocr" in contract_report
    assert "chunks_count" in contract_report
    assert "legal_sources" in contract_report
    assert "quotes" not in contract_report
    assert contract_report["legal_sources"][0]["trust_tier"] == "grounded | model_reported"


def test_report_schema_contains_legal_source_trust_tier() -> None:
    source = _sample_report()["legal_sources"][0]
    assert source["trust_tier"] in {"grounded", "model_reported"}
