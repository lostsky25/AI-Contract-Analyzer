from app.agents.document_qa_agent import (
    DocumentQAAgent,
    NO_INFO_ANSWER,
    _citations_from_chunks,
    _format_evidence,
    _resolve_chunk_id,
)


def test_chunk_id_from_metadata() -> None:
    item = {"metadata": {"chunk_index": 3}}
    assert _resolve_chunk_id(item, "doc-1") == "doc-1_3"


def test_chunk_id_from_top_level() -> None:
    item = {"chunk_id": "doc-1_5", "text": "sample"}
    assert _resolve_chunk_id(item, "doc-1") == "doc-1_5"


def test_format_evidence_includes_chunk_ids_and_page() -> None:
    evidence = _format_evidence(
        [
            {
                "text": "Стороны вправе расторгнуть договор.",
                "chunk_id": "doc-1_0",
                "page": 2,
            }
        ],
        "doc-1",
    )
    assert "chunk_id=doc-1_0" in evidence
    assert "page=2" in evidence
    assert "расторгнуть" in evidence


def test_citations_use_page_from_retrieval() -> None:
    citations = _citations_from_chunks(
        [{"text": "Payment net 30.", "page": 4, "chunk_id": "doc-1_0"}],
        "doc-1",
    )
    assert citations[0]["page"] == 4
    assert citations[0]["chunk_id"] == "doc-1_0"


def test_run_returns_no_info_when_no_chunks(monkeypatch) -> None:
    def fake_retrieval(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "app.agents.document_qa_agent.semantic_retrieval",
        fake_retrieval,
    )

    agent = DocumentQAAgent()
    result = agent.run(document_id="doc-1", question="Какие штрафы?")

    assert result["answer"] == NO_INFO_ANSWER
    assert result["confidence"] == "low"
    assert result["citations"] == []
