from fastapi.testclient import TestClient


def test_analyze_returns_analyzed_with_mocked_llm(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_analyze_contract(context: str) -> dict:
        assert context
        return {
            "summary": "Mocked summary",
            "risks": [
                {
                    "type": "Payment Risk",
                    "severity": "medium",
                    "description": "Late fee clause is ambiguous.",
                    "recommendation": "Clarify late fee calculation.",
                }
            ],
        }

    monkeypatch.setattr("app.api.routes.analyze_contract", fake_analyze_contract)

    response = client.post(
        "/api/analyze",
        json={"text": "Payment terms and termination clauses for review."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "analyzed"
    assert payload["summary"]
    assert isinstance(payload["risks"], list)
    assert payload["risks"]
