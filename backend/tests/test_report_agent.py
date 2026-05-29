from app.agents.report_agent import ReportAgent


def test_report_agent_fills_missing_quote_and_page() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-1",
            "status": "done",
            "summary": "Summary",
            "overall_risk": "medium",
            "risks": [
                {
                    "title": "Late payment",
                    "severity": "high",
                    "explanation": "Penalty applies after 10 days.",
                }
            ],
            "key_terms": [{"title": "Duration", "value": "12 months"}],
            "legal_sources": [],
            "warnings": [],
        }
    )

    assert report["risks"][0]["quote"] == "Penalty applies after 10 days."
    assert report["risks"][0]["page"] is None
    assert report["key_terms"][0]["quote"] == "12 months"


def test_report_agent_normalizes_legal_sources_and_deduplicates() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-2",
            "status": "done",
            "summary": "Summary",
            "overall_risk": "high",
            "risks": [
                {"title": "Risk", "severity": "CRITICAL", "explanation": "A", "quote": "A"},
                {"title": "Risk", "severity": "critical", "explanation": "A", "quote": "A"},
            ],
            "key_terms": [
                {"title": "Term", "value": "X", "quote": "X"},
                {"title": "Term", "value": "X", "quote": "X"},
            ],
            "legal_sources": [
                {
                    "title": "Src",
                    "url": "https://www.consultant.ru/document/1",
                    "snippet": "s",
                    "source_type": "bad_value",
                    "relevance": "VERY_HIGH",
                },
                {
                    "title": "Src",
                    "url": "https://www.consultant.ru/document/1",
                    "snippet": "s",
                    "source_type": "consultant_plus",
                    "relevance": "high",
                },
            ],
            "warnings": [],
            "used_ocr": False,
            "chunks_count": 1,
        }
    )

    assert len(report["risks"]) == 1
    assert report["risks"][0]["severity"] == "unknown"
    assert len(report["key_terms"]) == 1
    assert len(report["legal_sources"]) == 1
    assert report["legal_sources"][0]["source_type"] == "consultant_plus"
    assert report["legal_sources"][0]["relevance"] == "unknown"


def test_report_agent_fallback_on_invalid_sections() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-3",
            "status": "done",
            "summary": "Summary",
            "overall_risk": "low",
            "risks": "bad",
            "key_terms": "bad",
            "legal_sources": "bad",
            "warnings": [],
            "used_ocr": False,
            "chunks_count": 1,
        }
    )

    assert report["status"] == "done_with_warnings"
    assert report["risks"] == []
    assert report["key_terms"] == []
    assert report["legal_sources"] == []
    assert report["warnings"]
