# Frontend (React + Vite)

## Run

```bash
npm install
npm run dev
```

By default frontend expects backend API at:

`http://localhost:8000/api`

For local dev, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL` if needed.

## Implemented MVP flow

1. `POST /api/upload`
2. `POST /api/process`
3. `POST /api/analyze`
4. `GET /api/documents` and `GET /api/documents/{id}` for status refresh
