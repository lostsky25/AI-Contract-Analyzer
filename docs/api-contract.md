# API Contract (Agent-based MVP)

## Existing endpoints (already implemented in backend)

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/upload`
- `POST /api/extract`
- `POST /api/process`
- `POST /api/chunk`
- `POST /api/index`
- `POST /api/retrieve`
- `POST /api/analyze`
- `POST /api/orchestrate`
- `POST /api/ocr`
- `GET /api/documents`
- `GET /api/documents/{document_id}`

## Agent workflow contract (added as stable API layer)

- `POST /api/documents`
  - Request: multipart form (`file`)
  - Response:
    ```json
    {
      "document_id": "string",
      "filename": "string",
      "status": "uploaded"
    }
    ```

- `GET /api/documents/{document_id}/status`

- `POST /api/documents/{document_id}/analyze`
  - Runs full workflow:
    `DocumentProcessingAgent -> RetrievalAgent -> LegalRiskAgent -> KeyTermsAgent -> LegalResearchAgent -> ReportAgent`

- `GET /api/documents/{document_id}/report`

- `POST /api/documents/{document_id}/ask`
  - Body:
    ```json
    { "question": "string" }
    ```
  - Uses `DocumentQAAgent`.

- `GET /api/documents/{document_id}/legal-sources`
  - Optional helper to fetch legal research results separately.

## Legal research constraints

- Legal research uses public pages only.
- No paywall bypass.
- No login automation for closed systems.
- No claim of full access to consultant/garant private content.
- If sources are unavailable, API may return empty `legal_sources` and warnings without failing the full analysis.
