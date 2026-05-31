# Agent Workflow

## Pipeline

1. `upload` endpoint stores file metadata (`status=uploaded`).
2. `process` extracts contract text, builds chunk records, and returns OCR metadata.
3. `orchestrate` runs contract-first analysis and report assembly.
4. `documents/{id}/report` returns the latest normalized report payload.
5. `documents/{id}/ask` answers only from contract chunks (no web search).

## Contract-first rule

- `risks` and `key_terms` are derived only from contract evidence.
- Legal web sources are collected only after validated contract signals exist.
- `legal_sources` are returned in a separate array and are never embedded into `risks` or `key_terms`.
- `legal_sources` are external references only and are never treated as contract evidence.

## Grounding rule

- Published `risk` requires `quote`; `page` and `chunk_id` are included when available.
- Published `key_term` requires `quote`; `page` and `chunk_id` are included when available.
- Ungrounded items are rejected and converted into warning-level events instead of crashing the pipeline.

## Status policy

Canonical statuses used by API/docs:

- `uploaded`
- `processing`
- `processed`
- `analyzing`
- `done`
- `done_with_warnings`
- `failed`
- `failed_processing`

Legacy compatibility statuses that can still appear in old flows:

- `analyzed`
- `indexed`
- `extracted`
- `ocr_completed`
- `empty_text`

Report-level interpretation:

- `done`: report assembled, no warning-level issues.
- `done_with_warnings`: report assembled, warning-level issues exist.
- `failed`: no usable report assembled.

## Warnings policy

- Events are stored as `warnings: string[]`.
- `INFO:` prefix marks informational events.
- `INFO:` messages do not promote report status to `done_with_warnings`.
- Non-`INFO:` warnings promote status to `done_with_warnings`.

LegalResearch warning integration:

- `grounded` legal sources do not create warning by trust tier itself.
- `model_reported` legal sources always add a warning that manual verification is required.
- no metadata + no valid strict JSON produces warning and empty `legal_sources`.
- plain text links without valid JSON are rejected and produce warning.

Common warning-level examples:

- Tesseract OCR fallback used.
- Legal web search unavailable/failed.
- Some or all risks/key_terms rejected by grounding validator.
- Simplified fallback report assembly path used.

## Provider error policy

Canonical public error codes:

- `provider_missing_key`
- `provider_rate_limited`
- `provider_auth_failed`
- `provider_model_not_found`
- `provider_timeout`
- `provider_unavailable`
- `provider_bad_response`
- `provider_unknown_error`

Legacy compatibility:

- OpenRouter legacy codes (`openrouter_*`) are preserved in `legacy_code` when applicable.

Public error payload shape:

```json
{
  "detail": "string",
  "code": "provider_*",
  "provider": "bothub|openrouter",
  "retryable": true,
  "legacy_code": "openrouter_* | null"
}
```

## OCR metadata policy

- `used_ocr=true` is technical metadata and not an error by itself.
- Successful VLM OCR is represented as an `INFO:` event.
- Tesseract fallback is warning-level and can lead to `done_with_warnings`.
- `chunks_count` is backend metadata for retrieval/debug and may be hidden in UI.

## LegalResearch trust tiers

- `trust_tier=grounded`: source came from machine-readable metadata (`search_results`, `citations`, `annotations`, `results`, `sources`).
- `trust_tier=model_reported`: source came from strict model JSON fallback, passed domain/URL validation, and requires manual check.

Parser priority:

1. metadata extraction first;
2. strict JSON fallback only when metadata is absent and fallback flag is enabled;
3. plain text URLs are never accepted as legal sources.

## Legal and safety notes

- Public web pages only for legal research.
- No paywall/auth bypass.
- Output is preliminary contract analysis, not legal advice.
