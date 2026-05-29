from app.agents.report_agent import ReportAgent
from app.models.schemas import OrchestrateResponse
from helpers.report_validation import (
    validate_legal_sources_state,
    validate_report_schema,
)


def _sample_report() -> dict:
    return {
        "document_id": "doc-schema-1",
        "status": "done_with_warnings",
        "summary": "Договор поставки с неустойкой и односторонним расторжением.",
        "overall_risk": "medium",
        "risks": [
            {
                "title": "Неустойка",
                "severity": "medium",
                "explanation": "Штраф 0.1% в день.",
                "quote": "неустойка 0.1%",
                "page": 1,
            }
        ],
        "key_terms": [
            {
                "title": "Срок оплаты",
                "value": "10 банковских дней",
                "quote": "Оплата производится в течение 10 банковских дней",
                "page": 1,
            }
        ],
        "legal_sources": [],
        "warnings": ["Legal web search provider is unavailable."],
        "disclaimer": "Система выполняет предварительный анализ и не заменяет профессионального юриста.",
        "used_ocr": False,
        "chunks_count": 2,
    }


def test_orchestrate_response_validates_sample_report() -> None:
    payload = _sample_report()
    model = OrchestrateResponse.model_validate(payload)
    assert model.document_id == "doc-schema-1"
    assert model.status == "done_with_warnings"


def test_validate_report_schema_accepts_complete_payload() -> None:
    errors = validate_report_schema(_sample_report())
    assert errors == []


def test_validate_legal_sources_empty_with_warnings() -> None:
    errors = validate_legal_sources_state(_sample_report())
    assert errors == []


def test_validate_legal_sources_empty_without_warnings_fails() -> None:
    report = _sample_report()
    report["warnings"] = []
    errors = validate_legal_sources_state(report)
    assert any("warnings" in message for message in errors)


def test_report_agent_fallback_report() -> None:
    agent = ReportAgent()
    normalized = agent.run(
        {
            "document_id": "doc-fallback",
            "status": "done",
            "summary": "Краткое описание.",
            "overall_risk": "low",
            "risks": [{"title": "Risk A", "severity": "low", "explanation": "Detail."}],
            "key_terms": [{"title": "Payment", "value": "30 days"}],
            "legal_sources": [],
            "warnings": ["provider unavailable"],
        }
    )

    assert normalized["status"] == "done_with_warnings"
    assert normalized["risks"][0]["quote"] == "Detail."
    assert normalized["key_terms"][0]["quote"] == "30 days"
    assert normalized["disclaimer"]
    assert validate_report_schema({**normalized, "used_ocr": False, "chunks_count": 1}) == []
