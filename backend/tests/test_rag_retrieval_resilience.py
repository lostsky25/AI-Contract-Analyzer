import sys
import types

import pytest

from app.agents.analysis_agent import INSUFFICIENT_EVIDENCE_WARNING
from app.agents.orchestrator import Orchestrator
from app.agents.retrieval_agent import (
    INDEX_UNAVAILABLE_FALLBACK_WARNING,
    INDEX_UNAVAILABLE_WARNING,
    RetrievalAgent,
)
from app.config import settings
from app.services import rag_service


@pytest.fixture(autouse=True)
def reset_embedding_state() -> None:
    snapshot_model_name = settings.embedding_model_name
    snapshot_embedding_model = rag_service._embedding_model
    snapshot_chroma_client = rag_service._chroma_client
    yield
    settings.embedding_model_name = snapshot_model_name
    rag_service._embedding_model = snapshot_embedding_model
    rag_service._chroma_client = snapshot_chroma_client


class _DocProcessingStub:
    def __init__(self, records: list[dict]) -> None:
        self._records = records

    def run(self, _document_id: str, _file_path: str) -> dict:
        full_text = "\n".join(record["text"] for record in self._records)
        return {
            "raw": {
                "full_text": full_text,
                "used_ocr": False,
                "chunks_count": len(self._records),
                "text_preview": full_text[:120],
                "text_length": len(full_text),
                "chunk_records": self._records,
                "pages": [{"page": 1, "text": full_text}],
                "warnings": [],
            }
        }


class _LegalStub:
    def run(self, **_kwargs) -> dict:
        return {"legal_sources": [], "warnings": []}


def _mock_grounded_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_ask_llm_json(*_args, **kwargs):
        user_prompt = str(kwargs.get("user_prompt", ""))
        if '"summary"' in user_prompt:
            return {
                "summary": "Contract summary.",
                "risks": [
                    {
                        "title": "Penalty",
                        "severity": "high",
                        "explanation": "Late payment penalty is present.",
                        "quote": "Penalty 0.1% per day of delay.",
                        "page": 1,
                        "chunk_id": "doc-large_0",
                    }
                ],
            }
        return {
            "key_terms": [
                {
                    "title": "Payment",
                    "value": "10 banking days",
                    "explanation": "Payment deadline is explicit.",
                    "quote": "Payment must be made within 10 banking days.",
                    "page": 1,
                    "chunk_id": "doc-large_0",
                }
            ]
        }

    monkeypatch.setattr("app.agents.analysis_agent.ask_llm_json", fake_ask_llm_json)
    monkeypatch.setattr("app.agents.analysis_agent.analyze_contract", lambda **_kwargs: {})


def _build_records() -> list[dict]:
    return [
        {
            "text": (
                "Payment must be made within 10 banking days. "
                "Penalty 0.1% per day of delay. "
                "Contract may be terminated on material breach."
            ),
            "page": 1,
            "chunk_id": "doc-large_0",
            "chunk_index": 0,
        },
        {
            "text": "Liability is limited to paid service amount.",
            "page": 2,
            "chunk_id": "doc-large_1",
            "chunk_index": 1,
        },
    ]


def test_embedding_model_name_local_sentence_transformer_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    rag_service._embedding_model = None

    fake_module = types.ModuleType("sentence_transformers")
    captured: dict[str, str] = {}

    class _FakeModel:
        def encode(self, chunks, **_kwargs):
            return [[0.1, 0.2] for _ in chunks]

    def fake_sentence_transformer(model_name: str):
        captured["model_name"] = model_name
        return _FakeModel()

    fake_module.SentenceTransformer = fake_sentence_transformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    model = rag_service.get_embedding_model()

    assert model is not None
    assert captured["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"


def test_remote_embedding_model_name_rejected_without_provider() -> None:
    settings.embedding_model_name = "text-embedding-3-large"
    rag_service._embedding_model = None

    with pytest.raises(ValueError, match="remote embedding model"):
        rag_service.get_embedding_model()


def test_empty_retrieval_with_existing_chunks_uses_fallback_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.agents.retrieval_agent.save_chunk_records", lambda _doc_id, records: len(records))
    monkeypatch.setattr("app.agents.retrieval_agent.batch_semantic_retrieval", lambda **_kwargs: [[], []])

    records = _build_records()
    result = RetrievalAgent().run(document_id="doc-large", text="", chunk_records=records)

    assert result["risk_context"]
    assert result["terms_context"]
    assert INDEX_UNAVAILABLE_FALLBACK_WARNING in result["warnings"]


def test_fallback_evidence_preserves_page_and_chunk_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agents.retrieval_agent.save_chunk_records", lambda _doc_id, records: len(records))
    monkeypatch.setattr("app.agents.retrieval_agent.batch_semantic_retrieval", lambda **_kwargs: [[], []])

    records = _build_records()
    result = RetrievalAgent().run(document_id="doc-large", text="", chunk_records=records)

    risk_item = result["risk_context"][0]
    assert risk_item["page"] == 1
    assert risk_item["chunk_id"] == "doc-large_0"


def test_chroma_save_failure_produces_index_warning_not_insufficient_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _build_records()
    _mock_grounded_llm(monkeypatch)

    def failing_save(_document_id: str, _records: list[dict]) -> int:
        raise ValueError("ChromaDB embedding dimension mismatch detected.")

    monkeypatch.setattr("app.agents.retrieval_agent.save_chunk_records", failing_save)
    monkeypatch.setattr(
        "app.agents.orchestrator.update_document_status",
        lambda **_kwargs: None,
    )

    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub(records)
    orchestrator.legal_research_agent = _LegalStub()

    report = orchestrator.run(
        db=object(),
        document_id="doc-large",
        file_path="/tmp/contract.docx",
        user_id="user-1",
    )

    assert report["status"] == "done_with_warnings"
    assert INDEX_UNAVAILABLE_WARNING in report["warnings"]
    assert INSUFFICIENT_EVIDENCE_WARNING not in report["warnings"]


def test_large_docx_does_not_result_in_zero_risks_due_to_empty_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _build_records()
    _mock_grounded_llm(monkeypatch)

    monkeypatch.setattr("app.agents.retrieval_agent.save_chunk_records", lambda _doc_id, saved_records: len(saved_records))
    monkeypatch.setattr("app.agents.retrieval_agent.batch_semantic_retrieval", lambda **_kwargs: [[], []])
    monkeypatch.setattr(
        "app.agents.orchestrator.update_document_status",
        lambda **_kwargs: None,
    )

    orchestrator = Orchestrator()
    orchestrator.document_processing_agent = _DocProcessingStub(records)
    orchestrator.legal_research_agent = _LegalStub()

    report = orchestrator.run(
        db=object(),
        document_id="doc-large",
        file_path="/tmp/contract.docx",
        user_id="user-1",
    )

    assert len(report["risks"]) > 0
    assert len(report["key_terms"]) > 0
    assert INSUFFICIENT_EVIDENCE_WARNING not in report["warnings"]
    assert INDEX_UNAVAILABLE_FALLBACK_WARNING in report["warnings"] or INDEX_UNAVAILABLE_WARNING in report["warnings"]
