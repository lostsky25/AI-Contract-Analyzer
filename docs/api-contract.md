# API Contract

Актуальный контракт для backend API (`/api/*`). Документ отражает текущие маршруты и публичные схемы без внутренних служебных полей.

## Базовые эндпоинты

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

## Документы и анализ

- `POST /api/upload` — загрузка файла (legacy upload endpoint).
- `POST /api/documents` — загрузка файла (основной endpoint).
- `GET /api/documents` — список документов пользователя.
- `GET /api/documents/{document_id}` — карточка документа.
- `GET /api/documents/{document_id}/status` — статус обработки/анализа.
- `POST /api/process` — извлечение текста + OCR при необходимости + индексация chunks.
- `POST /api/orchestrate` — полный агентный пайплайн по `document_id`.
- `POST /api/documents/{document_id}/analyze` — обертка полного пайплайна по документу.
- `GET /api/documents/{document_id}/report` — итоговый отчет.
- `GET /api/documents/{document_id}/legal-sources` — правовые источники и предупреждения.
- `POST /api/documents/{document_id}/ask` — Q&A только по загруженному договору.

## Технические/служебные MVP-эндпоинты

- `POST /api/extract`
- `POST /api/chunk`
- `POST /api/index`
- `POST /api/retrieve`
- `POST /api/analyze`
- `POST /api/ocr`

## Ключевые request/response формы

### `POST /api/documents`

Response:

```json
{
  "document_id": "string",
  "filename": "string",
  "status": "uploaded"
}
```

### `POST /api/documents/{document_id}/analyze`

Request (optional):

```json
{
  "legal_web_search_enabled": true
}
```

Response: `OrchestrateResponse`.

### `GET /api/documents/{document_id}/report`

Response shape:

```json
{
  "document_id": "string",
  "status": "done | done_with_warnings | failed",
  "summary": "string",
  "overall_risk": "low | medium | high | unknown",
  "risks": [],
  "key_terms": [],
  "legal_sources": [],
  "warnings": ["string"],
  "disclaimer": "string",
  "used_ocr": true,
  "chunks_count": 0
}
```

### `POST /api/documents/{document_id}/ask`

Request:

```json
{
  "question": "Какие пункты требуют согласования с юристом?"
}
```

Response:

```json
{
  "document_id": "string",
  "question": "string",
  "answer": "string",
  "confidence": "low | medium | high | unknown",
  "citations": [
    {
      "quote": "string",
      "page": 1,
      "chunk_id": "string"
    }
  ],
  "disclaimer": "string"
}
```

### `GET /api/documents/{document_id}/legal-sources`

Response:

```json
{
  "document_id": "string",
  "legal_sources": [],
  "warnings": ["string"]
}
```

## Статусы и предупреждения

Канонические статусы отчета:

- `done`
- `done_with_warnings`
- `failed`

`warnings` всегда остаются в API-ответе. Префикс `INFO:` используется для информационных сообщений и не должен трактоваться как критическая ошибка.

## Политика LegalResearch

- Источники ограничены публичными страницами разрешенных доменов.
- `legal_sources` отделены от `risks`/`key_terms`.
- `trust_tier=model_reported` означает необходимость ручной проверки.

## Ошибки AI provider

Для провайдерных сбоев API возвращает нормализованные коды:

- `provider_missing_key`
- `provider_rate_limited`
- `provider_auth_failed`
- `provider_model_not_found`
- `provider_timeout`
- `provider_unavailable`
- `provider_bad_response`
- `provider_unknown_error`

Error payload:

```json
{
  "detail": "string",
  "code": "provider_*",
  "provider": "bothub | openrouter",
  "retryable": true,
  "legacy_code": "openrouter_* | null"
}
```

## Важные ограничения

- API не раскрывает внутренние server-side пути хранения файлов.
- Сервис выполняет предварительный анализ и не является юридической консультацией.
