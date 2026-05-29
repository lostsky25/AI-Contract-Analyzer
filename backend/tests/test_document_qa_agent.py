from app.agents.document_qa_agent import (
    DocumentQAAgent,
    NO_INFO_ANSWER,
    _chunk_id,
    _format_evidence,
)


def test_chunk_id_from_metadata() -> None:
    assert _chunk_id("doc-1", {"chunk_index": 3}) == "doc-1_3"


def test_format_evidence_includes_chunk_ids() -> None:
    evidence = _format_evidence(
        [
            {
                "text": "Стороны вправе расторгнуть договор.",
                "metadata": {"chunk_index": 0, "document_id": "doc-1"},
            }
        ],
        "doc-1",
    )
    assert "chunk_id=doc-1_0" in evidence
    assert "расторгнуть" in evidence


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
