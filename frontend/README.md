# Frontend (React + Vite)

## Run

```bash
npm install
npm run dev
```

By default frontend expects backend API at:

`http://localhost:8000/api`

Override with `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Implemented MVP flow

1. `POST /api/upload`
2. `POST /api/process`
3. `POST /api/analyze`
4. `GET /api/documents` and `GET /api/documents/{id}` for status refresh
