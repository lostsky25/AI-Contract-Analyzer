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

## Security

- Do not commit `backend/.env` or `frontend/.env`.
- Do not put real keys in `*.env.example`.
