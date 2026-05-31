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

    def extract_key_terms_with_grounding(self, context: list[dict]) -> dict:
        return {"key_terms": self.extract_key_terms(context), "warnings": []}

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


def test_orchestrator_sets_done_with_warnings_from_tesseract_fallback_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    fallback_warning = "Local OCR fallback was used. OCR quality may be lower."
    orchestrator = _build_orchestrator(
        process_warnings=[fallback_warning],
        legal_result={"legal_sources": [], "warnings": []},
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-ocr-warning",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert any(("резервный OCR" in warning) or ("Local OCR fallback" in warning) for warning in report["warnings"])
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


def test_grounded_sources_do_not_create_warning_by_trust_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=[],
        legal_result={
            "legal_sources": [
                {
                    "title": "Grounded",
                    "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                    "snippet": "Grounded snippet",
                    "source_type": "consultant_plus",
                    "relevance": "high",
                    "trust_tier": "grounded",
                }
            ],
            "warnings": [],
        },
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-grounded-only",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done"
    assert report["warnings"] == []
    assert statuses[-1] == "done"


def test_model_reported_sources_make_report_done_with_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = _build_orchestrator(
        process_warnings=[],
        legal_result={
            "legal_sources": [
                {
                    "title": "Model reported",
                    "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                    "snippet": "Model snippet",
                    "source_type": "consultant_plus",
                    "relevance": "medium",
                    "trust_tier": "model_reported",
                }
            ],
            "warnings": ["Sources were taken from the model-structured response and require manual verification."],
        },
    )

    report = orchestrator.run(
        db=object(),
        document_id="doc-status-model-reported",
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


def test_orchestrator_passes_only_validated_risks_to_legal_research(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub([])
    orchestrator.retrieval_agent = _RetrievalStub()

    class _ValidatedAnalysisStub:
        def analyze_risks(self, _context: list[dict]) -> dict:
            return {
                "summary": "Summary",
                "risks": [
                    {
                        "title": "Validated risk",
                        "severity": "medium",
                        "explanation": "Validated",
                        "quote": "validated quote",
                        "page": 1,
                    }
                ],
                "warnings": ["Р§Р°СЃС‚СЊ СЂРёСЃРєРѕРІ Р±С‹Р»Р° РѕС‚Р±СЂРѕС€РµРЅР°, РїРѕС‚РѕРјСѓ С‡С‚Рѕ РЅРµ РїРѕРґС‚РІРµСЂР¶РґР°Р»Р°СЃСЊ С†РёС‚Р°С‚Р°РјРё РёР· РґРѕРіРѕРІРѕСЂР°."],
            }

        def extract_key_terms_with_grounding(self, _context: list[dict]) -> dict:
            return {
                "key_terms": [
                    {
                        "title": "Validated term",
                        "value": "value",
                        "quote": "validated term quote",
                        "page": 1,
                    }
                ],
                "warnings": [],
            }

        def assemble_report(self, **kwargs) -> dict:
            return {
                "document_id": kwargs["document_id"],
                "status": "done",
                "summary": kwargs["risk_output"]["summary"],
                "overall_risk": "medium",
                "risks": kwargs["risk_output"]["risks"],
                "key_terms": kwargs["key_terms"],
                "legal_sources": [],
                "warnings": [],
                "used_ocr": kwargs["used_ocr"],
                "chunks_count": kwargs["chunks_count"],
            }

    orchestrator.analysis_agent = _ValidatedAnalysisStub()

    captured: dict[str, list[dict]] = {}

    class _LegalStub:
        def run(self, **kwargs):
            captured["risks"] = list(kwargs.get("risks", []))
            captured["key_terms"] = list(kwargs.get("key_terms", []))
            return {"legal_sources": [], "warnings": []}

    orchestrator.legal_research_agent = _LegalStub()

    report = orchestrator.run(
        db=object(),
        document_id="doc-validated-signals",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert len(captured["risks"]) == 1
    assert captured["risks"][0]["title"] == "Validated risk"
    assert len(captured["key_terms"]) == 1
    assert captured["key_terms"][0]["title"] == "Validated term"
    assert report["status"] == "done_with_warnings"
    assert statuses[-1] == "done_with_warnings"


def test_all_risks_rejected_pipeline_still_returns_report_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub([])
    orchestrator.retrieval_agent = _RetrievalStub()

    class _NoRisksAnalysisStub:
        def analyze_risks(self, _context: list[dict]) -> dict:
            return {
                "summary": "Summary",
                "risks": [],
                "warnings": [
                    "Р РёСЃРєРё РЅРµ Р±С‹Р»Рё РѕРїСѓР±Р»РёРєРѕРІР°РЅС‹, РїРѕС‚РѕРјСѓ С‡С‚Рѕ РЅРµ СѓРґР°Р»РѕСЃСЊ РїРѕРґС‚РІРµСЂРґРёС‚СЊ РёС… С†РёС‚Р°С‚Р°РјРё РёР· РґРѕРіРѕРІРѕСЂР°."
                ],
            }

        def extract_key_terms_with_grounding(self, _context: list[dict]) -> dict:
            return {"key_terms": [], "warnings": []}

        def assemble_report(self, **kwargs) -> dict:
            return {
                "document_id": kwargs["document_id"],
                "status": "done",
                "summary": kwargs["risk_output"]["summary"],
                "overall_risk": "unknown",
                "risks": kwargs["risk_output"]["risks"],
                "key_terms": kwargs["key_terms"],
                "legal_sources": [],
                "warnings": [],
                "used_ocr": kwargs["used_ocr"],
                "chunks_count": kwargs["chunks_count"],
            }

    orchestrator.analysis_agent = _NoRisksAnalysisStub()
    orchestrator.legal_research_agent = type("LegalStub", (), {"run": lambda *args, **kwargs: {"legal_sources": [], "warnings": []}})()

    report = orchestrator.run(
        db=object(),
        document_id="doc-no-risks",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert report["warnings"]
    assert statuses[-1] == "done_with_warnings"


def test_all_key_terms_rejected_pipeline_still_returns_report_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = _capture_status_updates(monkeypatch)
    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub([])
    orchestrator.retrieval_agent = _RetrievalStub()

    class _NoTermsAnalysisStub:
        def analyze_risks(self, _context: list[dict]) -> dict:
            return {
                "summary": "Summary",
                "risks": [],
                "warnings": [],
            }

        def extract_key_terms_with_grounding(self, _context: list[dict]) -> dict:
            return {
                "key_terms": [],
                "warnings": [
                    "РљР»СЋС‡РµРІС‹Рµ СѓСЃР»РѕРІРёСЏ РЅРµ Р±С‹Р»Рё РѕРїСѓР±Р»РёРєРѕРІР°РЅС‹, РїРѕС‚РѕРјСѓ С‡С‚Рѕ РЅРµ СѓРґР°Р»РѕСЃСЊ РїРѕРґС‚РІРµСЂРґРёС‚СЊ РёС… С†РёС‚Р°С‚Р°РјРё РёР· РґРѕРіРѕРІРѕСЂР°."
                ],
            }

        def assemble_report(self, **kwargs) -> dict:
            return {
                "document_id": kwargs["document_id"],
                "status": "done",
                "summary": kwargs["risk_output"]["summary"],
                "overall_risk": "unknown",
                "risks": kwargs["risk_output"]["risks"],
                "key_terms": kwargs["key_terms"],
                "legal_sources": [],
                "warnings": [],
                "used_ocr": kwargs["used_ocr"],
                "chunks_count": kwargs["chunks_count"],
            }

    orchestrator.analysis_agent = _NoTermsAnalysisStub()
    orchestrator.legal_research_agent = type("LegalStub", (), {"run": lambda *args, **kwargs: {"legal_sources": [], "warnings": []}})()

    report = orchestrator.run(
        db=object(),
        document_id="doc-no-terms",
        file_path="/tmp/demo.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert report["warnings"]
    assert statuses[-1] == "done_with_warnings"

