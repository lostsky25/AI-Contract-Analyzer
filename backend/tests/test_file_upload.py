from fastapi.testclient import TestClient


def test_upload_valid_pdf_returns_200(client: TestClient) -> None:
    files = {"file": ("sample.pdf", b"%PDF-1.4 test content", "application/pdf")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"]
    assert payload["filename"] == "sample.pdf"
    assert payload["status"] == "uploaded"


def test_upload_invalid_extension_returns_400(client: TestClient) -> None:
    files = {"file": ("malicious.exe", b"binary", "application/octet-stream")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 400
    payload = response.json()
    assert "Invalid file type" in payload["detail"]
