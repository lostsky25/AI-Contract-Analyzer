# AI Contract Analyzer Backend

## Requirements

- Python 3.12

## Run locally

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

4. Set `DATABASE_URL` in `.env`:

   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_contract_analyzer
   ```

5. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

## Windows OCR setup

1. Install Tesseract OCR.
2. Install Poppler for Windows.
3. Set paths in `.env`:

   ```env
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   POPPLER_PATH=C:\poppler\Library\bin
   ```

## Available endpoints

- `GET /api/health`
- `POST /api/upload` (multipart/form-data, field name: `file`)
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `POST /api/ocr`

## Run tests

```bash
pytest
```
