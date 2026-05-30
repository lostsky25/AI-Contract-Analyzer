# Agent Workflow

## Agents and responsibilities

1. **OrchestratorAgent** (no LLM)  
   Coordinates the pipeline, updates document status, and assembles outputs.

2. **DocumentProcessingAgent** (no LLM)  
   Tools: `PyMuPDF`, `python-docx`, `Tesseract` (OCR fallback).  
   Output: `pages[]`, `chunk_records[]` (with `page`), `full_text`.

3. **RetrievalAgent** (no LLM)  
   Tools: embeddings + `ChromaDB`.  
   Indexes `chunk_records` with metadata: `document_id`, `chunk_id`, `page`.  
   Returns retrieval hits: `text`, `page`, `chunk_id`, `score`.  
   Model for embeddings: `nvidia/llama-nemotron-embed-vl-1b-v2:free` (config field `EMBEDDING_MODEL`; runtime can fallback to local sentence-transformers if needed).

4. **LegalRiskAgent** (LLM step, `AnalysisAgent.analyze_risks`)  
   Model: `OPENROUTER_MODEL_RISK` (`nvidia/nemotron-3-super-120b-a12b:free`)  
   Fallback: `OPENROUTER_MODEL_FALLBACK`.  
   Input: evidence pack from retrieval (`risk_context`).  
   Output: risks with `quote` and `page` (filled from evidence when LLM omits them).

5. **KeyTermsAgent** (LLM step, `AnalysisAgent.extract_key_terms`)  
   Model: `OPENROUTER_MODEL_KEY_TERMS` (`google/gemma-4-31b-it:free`)  
   Fallback: `OPENROUTER_MODEL_FALLBACK`.  
   Input: `terms_context` evidence pack.  
   Output: key terms with `quote` and `page`.

6. **LegalResearchAgent** (mandatory LLM + web search step)  
   Model: `OPENROUTER_MODEL_LEGAL_RESEARCH` (`openrouter/owl-alpha`)  
   Provider: `LEGAL_SEARCH_PROVIDER=openrouter_web_search`  
   Tool: `openrouter:web_search` with `allowed_domains` = `consultant.ru`, `garant.ru`, `pravo.gov.ru`  
   Input: `document_id`, `risks`, `key_terms`, `summary`  
   Output: `legal_sources[]`, `limitations`, `warnings`  
   If web search is unavailable: returns `legal_sources=[]`, report status may become `done_with_warnings`.

7. **ReportAgent** (no LLM)  
   Normalizes and validates report fields against `docs/report-schema.json`.  
   Safe fallback: missing `quote` в†ђ `explanation`/`value`; `page` may stay `null`.

### Page-aware pipeline notes

- **PDF:** one entry per PDF page; chunks inherit that page.
- **DOCX:** entire document as `page: 1` only вЂ” no real pagination in MVP (see `docs/api-contract.md`).
- **OCR:** PDF via `run_ocr_pages` is page-aware; scanned images use `page: 1`.

8. **DocumentQAAgent** (LLM step, RAG-only)  
   Model: `OPENROUTER_MODEL_QA` (`nvidia/nemotron-3-super-120b-a12b:free`)  
   Fallback: `OPENROUTER_MODEL_FALLBACK` (`deepseek/deepseek-v4-flash:free`)  
   Retrieval: `semantic_retrieval(document_id, question)` вЂ” top-k chunks from ChromaDB  
   **No web search** вЂ” answers only from uploaded contract text.

## Workflow

`Frontend upload -> Upload API -> OrchestratorAgent -> DocumentProcessingAgent -> RetrievalAgent -> LegalRiskAgent + KeyTermsAgent + LegalResearchAgent -> ReportAgent -> Frontend Report -> DocumentQAAgent for ask flow`

## LegalResearchAgent limitations (mandatory)

- Public web pages only (via OpenRouter `openrouter:web_search`).
- No authentication attempts on legal platforms.
- No paywall bypass.
- No claims about full access to closed legal databases (including Consultant Plus / Garant commercial sections).
- Search results are preliminary references, not verified legal advice.
- For production, use a legal provider/API with proper licensing instead of relying only on public page snippets.
- If results are unavailable, returns empty `legal_sources` with `limitations` and does not break full analysis (`done_with_warnings`).

## Guardrails summary

- User question is normalized and validated before Q&A (`normalize_user_question`).
- Prompt injection attempts in user input are refused with a safe response payload (HTTP 200).
- Off-topic questions are refused with a safe response payload (HTTP 200).
- DocumentQA answers are accepted only when citations are grounded in retrieved evidence.
- Contract and derived context are explicitly marked as untrusted data in AnalysisAgent and LegalResearchAgent prompts.

