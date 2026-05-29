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

    assert report["risks"][0]["quote"] == ""
    assert report["risks"][0]["page"] is None
    assert report["key_terms"][0]["quote"] == ""


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


def test_report_agent_deduplicates_legal_sources_by_normalized_url() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-2b",
            "status": "done",
            "summary": "Summary",
            "overall_risk": "medium",
            "risks": [],
            "key_terms": [],
            "legal_sources": [
                {
                    "title": "Src A",
                    "url": "https://www.consultant.ru/document/1/",
                    "snippet": "alpha",
                    "source_type": "consultant_plus",
                    "relevance": "high",
                },
                {
                    "title": "Src A duplicate",
                    "url": "https://www.consultant.ru/document/1#section",
                    "snippet": "beta",
                    "source_type": "consultant_plus",
                    "relevance": "medium",
                },
            ],
            "warnings": [],
        }
    )

    assert len(report["legal_sources"]) == 1
    assert report["legal_sources"][0]["url"] == "https://www.consultant.ru/document/1"


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


def test_report_agent_normalizes_generic_english_risk_titles_to_russian() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-lang-1",
            "status": "done",
            "summary": "Краткое резюме.",
            "overall_risk": "medium",
            "risks": [
                {
                    "title": "High penalties and service suspension for late payment",
                    "severity": "high",
                    "explanation": "Риск повышенных санкций.",
                    "quote": "Если просрочка более 30 дней, исполнитель вправе приостановить услуги.",
                    "page": 1,
                }
            ],
            "key_terms": [],
            "legal_sources": [],
            "warnings": [],
        }
    )
    assert report["risks"][0]["title"] == "Высокие штрафы и приостановка услуг за просрочку оплаты"


def test_report_agent_keeps_russian_key_terms_and_does_not_change_quote() -> None:
    agent = ReportAgent()
    quote = "Payment shall be made within 10 business days."
    report = agent.run(
        {
            "document_id": "doc-lang-2",
            "status": "done",
            "summary": "Краткое резюме.",
            "overall_risk": "low",
            "risks": [],
            "key_terms": [
                {
                    "title": "Срок оплаты",
                    "value": "10 рабочих дней",
                    "quote": quote,
                    "page": 2,
                }
            ],
            "legal_sources": [],
            "warnings": [],
        }
    )
    assert report["key_terms"][0]["title"] == "Срок оплаты"
    assert report["key_terms"][0]["value"] == "10 рабочих дней"
    assert report["key_terms"][0]["quote"] == quote


def test_report_agent_done_with_warnings_is_not_failed() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-lang-3",
            "status": "done",
            "summary": "Краткое резюме.",
            "overall_risk": "low",
            "risks": [],
            "key_terms": [],
            "legal_sources": [],
            "warnings": ["Legal web search provider is unavailable."],
        }
    )
    assert report["status"] == "done_with_warnings"
    assert report["status"] != "failed"
    assert report["warnings"]


def test_report_agent_keeps_russian_disclaimer() -> None:
    agent = ReportAgent()
    report = agent.run(
        {
            "document_id": "doc-lang-4",
            "status": "done",
            "summary": "Краткое резюме.",
            "overall_risk": "unknown",
            "risks": [],
            "key_terms": [],
            "legal_sources": [],
            "warnings": [],
        }
    )
    assert (
        report["disclaimer"]
        == "Система выполняет предварительный анализ и не заменяет профессионального юриста."
    )
