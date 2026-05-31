# Environment variables

## Recommended MVP setup

Use one shared BotHub key for all primary AI paths:

```env
BOTHUB_API_KEY=...
BOTHUB_API_BASE_URL=https://openai.bothub.chat/v1

LLM_PROVIDER=bothub
VISION_PROVIDER=bothub
LEGAL_RESEARCH_PROVIDER=bothub_sonar
LEGAL_WEB_SEARCH_ENABLED=true
LEGAL_RESEARCH_ALLOW_MODEL_REPORTED_SOURCES=true
```

BotHub is used for:
- Risk / KeyTerms / Q&A / text fallback
- Vision OCR
- LegalResearch

## Embeddings (MVP)

Use local SentenceTransformer embeddings in current MVP:

```env
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

`text-embedding-3-large` is a remote OpenAI-compatible embedding model and is not
supported by `EMBEDDING_MODEL_NAME` unless a remote embeddings provider is implemented.

## OCR tuning

Recommended defaults for scanned PDFs:

```env
OCR_PROVIDER=hybrid
OCR_USE_VLM=true
OCR_DEBUG=false
OCR_VLM_DPI=220
OCR_MIN_TEXT_CHARS_PER_PAGE=50
```

## LegalResearch fallback mode

Some BotHub Sonar-compatible models may return a normal JSON response body but omit
machine-readable `search_results` / `citations`.

If:

```env
LEGAL_RESEARCH_ALLOW_MODEL_REPORTED_SOURCES=true
```

backend may accept `legal_sources` from model JSON content only after strict validation:
- JSON must be valid and contain `legal_sources`
- only http/https URLs
- only allowed domains (`consultant.ru`, `garant.ru`, `pravo.gov.ru`)
- no placeholder/fake URLs (`https://...`, `example.com`, `localhost`, etc.)
- snippet/title/url required
- root-domain-only links (without concrete path) are rejected

If validation passes, report includes a warning that sources require manual verification.
Plain text links are not accepted.

Recommended toggles:

```env
LEGAL_RESEARCH_ALLOW_MODEL_REPORTED_SOURCES=true
LEGAL_RESEARCH_DEBUG=false
```

## OpenRouter (legacy fallback only)

OpenRouter is not required for default MVP setup.
Use it only when explicitly switching provider modes:

```env
LLM_PROVIDER=openrouter
VISION_PROVIDER=openrouter
LEGAL_RESEARCH_PROVIDER=openrouter_web_search
OPENROUTER_API_KEY=...
```

## Direct Perplexity

Direct Perplexity API mode is not used in current MVP architecture.
Do not add `PERPLEXITY_API_KEY` for normal project setup.

## Security

- Never commit `backend/.env`.
- Never print real keys in logs.
- If a key was exposed, rotate/revoke it.

## Runtime status and warnings

- `used_ocr=true` is expected metadata and does not mean request failure.
- `INFO:` messages (for example successful VLM OCR usage) do not force `done_with_warnings`.
- Non-`INFO:` warnings (for example local OCR fallback) can move report status to `done_with_warnings`.

## Provider error codes

Public API error responses use canonical `provider_*` codes and may include legacy OpenRouter code in `legacy_code`:

- `provider_missing_key`
- `provider_rate_limited`
- `provider_auth_failed`
- `provider_model_not_found`
- `provider_timeout`
- `provider_unavailable`
- `provider_bad_response`
- `provider_unknown_error`

## Restart after `.env` changes

```powershell
docker compose down
docker compose up -d --build
```

## Docker runtime modes

Demo/default start (no API auto-reload):

```powershell
docker compose up -d --build
```

Dev start with API reload:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Check env without printing secrets

```powershell
docker compose exec api python -c "import os; print('BOTHUB_API_KEY', 'present' if os.getenv('BOTHUB_API_KEY') else 'missing')"
```
