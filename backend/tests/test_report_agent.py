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
