import pytest

from app.agents.orchestrator import Orchestrator
from app.services.text_extractor import VLM_OCR_INFO_MESSAGE


class _DocProcessingStub:
    def __init__(self, warnings: list[str] | None = None) -> None:
        self._warnings = warnings or []

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
                "warnings": self._warnings,
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


def _build_orchestrator(process_warnings: list[str], legal_result: dict | Exception) -> Orchestrator:
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub(process_warnings)
    orchestrator.retrieval_agent = _RetrievalStub()
    orchestrator.analysis_agent = _AnalysisStub()

    if isinstance(legal_result, Exception):
        orchestrator.legal_research_agent = type(
            "LegalStub",
            (),
            {"run": lambda *args, **kwargs: (_ for _ in ()).throw(legal_result)},
        )()
    else:
        orchestrator.legal_research_agent = type(
            "LegalStub",
            (),
            {"run": lambda *args, **kwargs: legal_result},
        )()
    return orchestrator


def _capture_status_updates(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    statuses: list[str] = []

    def fake_update_document_status(*, status: str, **_kwargs):
        statuses.append(status)
        return None

    monkeypatch.setattr("app.agents.orchestrator.update_document_status", fake_update_document_status)
    return statuses


def test_orchestrator_ignores_vlm_info_for_warning_status(monkeypatch: pytest.MonkeyPatch) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=[VLM_OCR_INFO_MESSAGE],
        legal_result={"legal_sources": [], "warnings": []},
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-info-only",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done"
    assert report["warnings"] == []
    assert statuses[-1] == "done"


def test_orchestrator_sets_done_with_warnings_from_process_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=["Used local OCR fallback."],
        legal_result={"legal_sources": [], "warnings": []},
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-ocr-warning",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert "Used local OCR fallback." in report["warnings"]
    assert statuses[-1] == "done_with_warnings"


def test_orchestrator_sets_done_with_warnings_from_legal_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=[],
        legal_result={
            "legal_sources": [],
            "warnings": ["Legal web search provider is unavailable."],
        },
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-legal-warning",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert report["warnings"]
    assert statuses[-1] == "done_with_warnings"


def test_orchestrator_handles_legal_research_exception_as_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=[],
        legal_result=RuntimeError("boom"),
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-2",
        file_path="/tmp/demo.docx",
        user_id="user-2",
    )

    assert report["status"] == "done_with_warnings"
    assert report["warnings"]
    assert statuses[-1] == "done_with_warnings"
