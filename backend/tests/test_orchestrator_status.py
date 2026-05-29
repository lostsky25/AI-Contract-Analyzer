import pytest

from app.agents.orchestrator import Orchestrator


class _DocProcessingStub:
    def run(self, _document_id: str, _file_path: str) -> dict:
        return {
            "raw": {
                "full_text": "text",
                "used_ocr": False,
                "chunks_count": 1,
                "text_preview": "text",
                "text_length": 4,
                "chunk_records": [],
                "pages": [],
            }
        }


class _RetrievalStub:
    def run(self, **_kwargs) -> dict:
        return {
            "risk_context": [{"text": "risk", "page": 1, "chunk_id": "c1"}],
            "terms_context": [{"text": "term", "page": 1, "chunk_id": "c2"}],
            "chunks_count": 2,
        }


class _AnalysisStub:
    def analyze_risks(self, _context: list[dict]) -> dict:
        return {
            "summary": "Summary",
            "risks": [
                {
                    "title": "Penalty",
                    "severity": "high",
                    "explanation": "Penalty clause",
                    "quote": "Penalty clause",
                    "page": 1,
                }
            ],
        }

    def extract_key_terms(self, _context: list[dict]) -> list[dict]:
        return [{"title": "Payment", "value": "10 days", "quote": "10 days", "page": 1}]

    def assemble_report(
        self,
        document_id: str,
        risk_output: dict,
        key_terms: list[dict],
        used_ocr: bool,
        chunks_count: int,
    ) -> dict:
        return {
            "document_id": document_id,
            "status": "done",
            "summary": risk_output["summary"],
            "overall_risk": "high",
            "risks": risk_output["risks"],
            "key_terms": key_terms,
            "legal_sources": [],
            "warnings": [],
            "used_ocr": used_ocr,
            "chunks_count": chunks_count,
        }


def test_orchestrator_sets_done_with_warnings_from_legal_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses: list[str] = []
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub()
    orchestrator.retrieval_agent = _RetrievalStub()
    orchestrator.analysis_agent = _AnalysisStub()
    orchestrator.legal_research_agent = type(
        "LegalStub",
        (),
        {
            "run": lambda *args, **kwargs: {
                "legal_sources": [],
                "warnings": ["Legal web search provider is unavailable."],
            }
        },
    )()

    def fake_update_document_status(*, status: str, **_kwargs):
        statuses.append(status)
        return None

    monkeypatch.setattr("app.agents.orchestrator.update_document_status", fake_update_document_status)

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-1",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert statuses[-1] == "done_with_warnings"


def test_orchestrator_handles_legal_research_exception_as_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses: list[str] = []
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub()
    orchestrator.retrieval_agent = _RetrievalStub()
    orchestrator.analysis_agent = _AnalysisStub()
    orchestrator.legal_research_agent = type(
        "LegalStub",
        (),
        {"run": lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))},
    )()

    def fake_update_document_status(*, status: str, **_kwargs):
        statuses.append(status)
        return None

    monkeypatch.setattr("app.agents.orchestrator.update_document_status", fake_update_document_status)

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-2",
        file_path="/tmp/demo.docx",
        user_id="user-2",
    )

    assert report["status"] == "done_with_warnings"
    assert report["warnings"]
    assert statuses[-1] == "done_with_warnings"
