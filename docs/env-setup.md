# Environment variables

## Files

| File | In git | Purpose |
|------|--------|---------|
| `backend/.env.example` | Yes | Template — copy to `backend/.env` |
| `backend/.env` | No | API secrets and settings |
| `frontend/.env.example` | Yes | Template for local Vite |
| `frontend/.env` | No | Optional; only for `npm run dev` outside Docker |

There is **no** root `.env` — backend and frontend each have their own.

## Setup

```bash
cp backend/.env.example backend/.env
# set OPENROUTER_API_KEY in backend/.env

# optional, local frontend only:
cp frontend/.env.example frontend/.env
```

## Docker Compose

- **api** — `env_file: backend/.env`; compose overrides `DATABASE_URL`, `UPLOAD_DIR`, `CHROMA_DB_DIR`, OCR paths for the container.
- **frontend** — `VITE_API_BASE_URL` defaults to `http://localhost:8000/api` in `docker-compose.yml` (no root `.env` required).

FastAPI loads `backend/.env` by absolute path (`app/config.py`).

## OCR settings (hybrid provider)

- `OCR_PROVIDER=hybrid` — uses PDF text layer first, then OCR for weak/empty pages.
- `OCR_USE_VLM=true` — enables OpenRouter Vision OCR for scanned/low-quality pages.
- `OPENROUTER_MODEL_OCR_VLM` — optional dedicated Vision model override.
- `OCR_VLM_MAX_PAGES=20` — max pages for VLM OCR pass.
- `OCR_VLM_DPI=160` — page rendering DPI for Vision OCR.
- `OCR_VLM_TIMEOUT_SECONDS=120` — timeout for one VLM OCR request.
- `OCR_MIN_TEXT_CHARS_PER_PAGE=50` — threshold to treat page text layer as too weak.

## Security

- Do not commit `backend/.env` or `frontend/.env`.
- Do not put real keys in `*.env.example`.
