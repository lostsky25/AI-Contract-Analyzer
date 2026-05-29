# AI Contract Analyzer Backend

## Requirements

- Python 3.12 (for local run)
- Docker + Docker Compose (recommended)

## Run with Docker (recommended)

From the project root:

1. Optional: create `.env` in project root for secrets (e.g. OpenRouter):

   ```bash
   cp .env.example .env
   ```

2. Start services:

   ```bash
   docker compose up --build
   ```

3. Open services:

   - API: http://localhost:8000
   - Swagger: http://localhost:8000/docs
   - Frontend: http://localhost:5173

Services:

- `api` — FastAPI backend (port `8000`)
- `db` — PostgreSQL 16 (port `5432`)
- `frontend` — React + Vite (port `5173`)

Data is persisted in Docker volumes and local folders:

- `backend/uploads/`
- `backend/chroma_db/`
- PostgreSQL volume `postgres_data`

Stop:

```bash
docker compose down
```

First startup may take several minutes while embedding models are downloaded.

## Run locally (without Docker)

1. Create and activate a virtual environment:

   Windows (PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create PostgreSQL database:

   ```sql
   CREATE DATABASE ai_contract_analyzer;
   ```

4. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL`.

5. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

## Windows OCR setup (local only)

Inside Docker, Tesseract and Poppler are preinstalled.

For local Windows run:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\poppler\Library\bin
```

## Available endpoints

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me` (Bearer token)
- `POST /api/upload` (multipart/form-data, field name: `file`)
- `POST /api/extract`
- `POST /api/process`
- `POST /api/chunk`
- `POST /api/index`
- `POST /api/retrieve`
- `POST /api/analyze`
- `POST /api/ocr`
- `GET /api/documents`
- `GET /api/documents/{document_id}`

## Example curl (Docker)

```bash
curl http://localhost:8000/api/health

curl -X POST http://localhost:8000/api/upload \
  -F "file=@backend/test_data/sample.docx"
```

## Auth quick start

Register:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"DemoPass123"}'
```

Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"DemoPass123"}'
```

`/auth/login` returns `access_token`. Use it as:

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## Run tests

```bash
cd backend
pytest
```

Tests use mocked DB and do not require Docker services.

Covered by pytest (no live API):

- `GET /api/health`
- Report schema validation and `ReportAgent` fallback
- `LegalResearchAgent` normalization and no-API-key fallback
- `GET /api/documents/{id}/status` and `/report` (mocked DB/orchestrator)
- `POST /api/documents/{id}/analyze` and `/ask` (mocked)

## Smoke test (live API)

From repository root, with API running on port 8000:

```powershell
pip install -r backend/requirements.txt
python scripts/smoke_backend.py
```

```bash
bash scripts/smoke_backend.sh
```

| Step | Endpoint | Requires `OPENROUTER_API_KEY` |
|------|----------|----------------------------------|
| Health | `GET /api/health` | No |
| Register/login | `/api/auth/*` | No |
| Upload demo DOCX | `POST /api/documents` | No |
| Full analyze | `POST /api/documents/{id}/analyze` | Yes |
| Report + legal_sources | `GET .../report`, `.../legal-sources` | Yes (after analyze) |
| Q&A + citations | `POST .../ask` | Yes |

Demo file: `backend/test_data/demo_contract.docx` (auto-created on first smoke run).

Without API key, smoke exits with code `2` after health/auth/upload — no stack trace.

Legal web search may return empty `legal_sources` with `warnings`; analyze must still succeed (`done` or `done_with_warnings`).
