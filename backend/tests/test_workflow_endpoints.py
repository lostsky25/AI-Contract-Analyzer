from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agents.report_agent import ReportAgent
from app.models.db_models import Document
from app.services import report_store
from helpers.demo_contract import write_demo_contract
from helpers.report_validation import (
    validate_legal_sources_state,
    validate_report_schema,
)


@pytest.fixture
def demo_docx(tmp_path: Path) -> Path:
    path = tmp_path / "demo_contract.docx"
    write_demo_contract(path)
    return path


@pytest.fixture
def workflow_document(demo_docx: Path) -> Document:
    return Document(
        id="workflow-doc-1",
        user_id="test-user-id",
        filename="demo_contract.docx",
        file_path=str(demo_docx),
        status="uploaded",
    )


def test_document_status_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    workflow_document: Document,
) -> None:
    def fake_get_document(_db, document_id: str, user_id: str | None = None):
        if document_id == workflow_document.id and user_id == "test-user-id":
            workflow_document.status = "done"
            return workflow_document
        return None

    monkeypatch.setattr("app.api.routes.get_document", fake_get_document)

    response = client.get(f"/api/documents/{workflow_document.id}/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == workflow_document.id
    assert payload["status"] == "done"


def test_document_report_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    workflow_document: Document,
) -> None:
    report = ReportAgent().run(
        {
            "document_id": workflow_document.id,
            "status": "done_with_warnings",
            "summary": "Договор поставки.",
            "overall_risk": "medium",
            "risks": [
                {
                    "title": "Неустойка",
                    "severity": "high",
                    "explanation": "0.1% в день.",
                    "quote": "неустойка 0.1%",
                    "page": 1,
                }
            ],
            "key_terms": [
                {
                    "title": "Оплата",
                    "value": "10 дней",
                    "quote": "10 банковских дней",
                    "page": 1,
                }
            ],
            "legal_sources": [],
            "warnings": ["Legal web search provider is unavailable."],
            "used_ocr": False,
            "chunks_count": 3,
        }
    )
    report_store.save_report(workflow_document.id, report)

    def fake_get_document(_db, document_id: str, user_id: str | None = None):
        if document_id == workflow_document.id and user_id == "test-user-id":
            return workflow_document
        return None

    monkeypatch.setattr("app.api.routes.get_document", fake_get_document)

    response = client.get(f"/api/documents/{workflow_document.id}/report")
    assert response.status_code == 200
    payload = response.json()
    assert validate_report_schema(payload) == []
    assert validate_legal_sources_state(payload) == []
    assert payload["disclaimer"]
    assert isinstance(payload["legal_sources"], list)


def test_document_analyze_endpoint_with_mocked_orchestrator(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    workflow_document: Document,
) -> None:
    mock_report = ReportAgent().run(
        {
            "document_id": workflow_document.id,
            "status": "done_with_warnings",
            "summary": "Smoke mock summary.",
            "overall_risk": "low",
            "risks": [
                {
                    "title": "Termination",
                    "severity": "medium",
                    "explanation": "Unilateral termination clause.",
                    "quote": "расторгнут",
                    "page": 1,
                }
            ],
            "key_terms": [
                {
                    "title": "Payment",
                    "value": "10 days",
                    "quote": "10 банковских дней",
                    "page": 1,
                }
            ],
            "legal_sources": [
                {
                    "title": "ГК РФ",
                    "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                    "snippet": "Обязательства сторон.",
                    "source_type": "consultant_plus",
                    "relevance": "medium",
                    "trust_tier": "grounded",
                    "reason": "Relevant to obligations.",
                }
            ],
            "warnings": ["Public sources only."],
            "used_ocr": False,
            "chunks_count": 2,
        }
    )

    def fake_get_document(_db, document_id: str, user_id: str | None = None):
        if document_id == workflow_document.id and user_id == "test-user-id":
            return workflow_document
        return None

    def fake_orchestrator_run(**_kwargs):
        report_store.save_report(workflow_document.id, mock_report)
        return mock_report

    monkeypatch.setattr("app.api.routes.get_document", fake_get_document)
    monkeypatch.setattr("app.api.routes.orchestrator.run", fake_orchestrator_run)

    response = client.post(f"/api/documents/{workflow_document.id}/analyze")
    assert response.status_code == 200
    payload = response.json()
    assert validate_report_schema(payload) == []
    assert payload["legal_sources"] or payload["warnings"]


def test_document_ask_returns_citations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    workflow_document: Document,
) -> None:
    def fake_get_document(_db, document_id: str, user_id: str | None = None):
        if document_id == workflow_document.id and user_id == "test-user-id":
            return workflow_document
        return None

    def fake_qa_run(document_id: str, question: str) -> dict:
        return {
            "document_id": document_id,
            "question": question,
            "answer": "Оплата в течение 10 банковских дней.",
            "confidence": "medium",
            "citations": [
                {
                    "quote": "Оплата производится в течение 10 банковских дней",
                    "page": 1,
                    "chunk_id": f"{document_id}_0",
                }
            ],
            "disclaimer": "Не юридическая консультация.",
        }

    monkeypatch.setattr("app.api.routes.get_document", fake_get_document)
    monkeypatch.setattr("app.api.routes.document_qa_agent.run", fake_qa_run)

    response = client.post(
        f"/api/documents/{workflow_document.id}/ask",
        json={"question": "Какой срок оплаты?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert len(payload["citations"]) >= 1
    assert payload["citations"][0]["quote"]
    assert payload["citations"][0]["chunk_id"]


def test_documents_upload_creates_document(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    demo_docx: Path,
) -> None:
    stored: list[Document] = []

    def fake_create_document(
        db,
        document_id: str,
        user_id: str,
        filename: str,
        file_path: str,
        status: str,
    ) -> Document:
        document = Document(
            id=document_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            status=status,
        )
        stored.append(document)
        return document

    monkeypatch.setattr("app.api.routes.create_document", fake_create_document)

    with demo_docx.open("rb") as handle:
        response = client.post(
            "/api/documents",
            files={
                "file": (
                    "demo_contract.docx",
                    handle,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"]
    assert payload["status"] == "uploaded"
    assert len(stored) == 1


