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

- `LegalResearchAgent` is a mandatory step in `POST /api/documents/{document_id}/analyze`.
- Uses OpenRouter server tool `openrouter:web_search` with domain filter:
  - `consultant.ru`
  - `garant.ru`
  - `pravo.gov.ru`
- Public web pages only; no paywall bypass; no login automation.
- No claim of full access to Consultant Plus / Garant commercial databases.
- Report may include:
  - `legal_sources[]` (title, url, snippet, source_type, relevance)
  - `warnings[]` (includes limitations text)
  - `status=done_with_warnings` when sources are empty but analysis completed
- Separate read endpoint: `GET /api/documents/{document_id}/legal-sources`

### Example: run analyze (requires auth token)

```bash
curl -X POST "http://localhost:8000/api/documents/{document_id}/analyze" \
  -H "Authorization: Bearer <token>"
```

### Example: read legal sources

```bash
curl "http://localhost:8000/api/documents/{document_id}/legal-sources" \
  -H "Authorization: Bearer <token>"
```

Response shape:

```json
{
  "document_id": "uuid",
  "legal_sources": [],
  "warnings": ["Legal web search provider is unavailable."]
}
```
