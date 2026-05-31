# AI Contract Analyzer

AI Contract Analyzer — MVP-система предварительного анализа договоров с помощью AI. Сервис извлекает текст из DOCX/PDF, при необходимости применяет OCR, определяет риски и ключевые условия с опорой на цитаты из договора, показывает правовые источники с trust-tier и отвечает на вопросы по документу.

> Важно: результат является предварительным анализом и не является юридической консультацией.

## Возможности

- Загрузка DOCX/PDF.
- OCR для сканов PDF и изображений.
- Выделение рисков договора.
- Выделение ключевых условий.
- Цитаты из договора (quote/page/chunk_id в отчете).
- Правовые источники с trust-tier (`grounded`, `model_reported`).
- Q&A по тексту договора.
- История документов и отчетов.
- Система предупреждений и дисклеймеров.

## Архитектура

- Frontend: React + Vite + TypeScript.
- Backend: FastAPI.
- База данных: PostgreSQL.
- Vector store: ChromaDB.
- Embeddings: локальная SentenceTransformer-модель `sentence-transformers/all-MiniLM-L6-v2`.
- Основной AI provider: BotHub (LLM, Vision OCR, LegalResearch).
- OpenRouter: только legacy fallback режим.

## Agent Pipeline

1. Upload.
2. Text extraction.
3. OCR (если нужно).
4. Chunking и RAG indexing.
5. Risk analysis.
6. Key terms extraction.
7. Legal research.
8. Report assembly.
9. Document Q&A.

## Safety и Guardrails

- `risks` и `key_terms` публикуются только при наличии contract evidence.
- `legal_sources` не считаются доказательством текста договора и возвращаются отдельным массивом.
- Q&A отвечает только по загруженному договору.
- Off-topic и prompt-injection запросы отклоняются.
- В отчете всегда сохраняется дисклеймер о предварительном характере анализа.

## LegalResearch Trust Model

- `grounded`: источник получен из machine-readable provider metadata.
- `model_reported`: источник получен из структурированного ответа модели и требует ручной проверки.
- Невалидные/plain-text/outside-domain/root-only URL отклоняются.

## Быстрый старт (Docker)

```powershell
cp backend/.env.example backend/.env
docker compose up -d --build
```

API docs: `http://localhost:8000/docs`

## Настройка .env (кратко)

Заполняются в `backend/.env` (без реальных ключей в репозитории):

- `BOTHUB_API_KEY`
- `BOTHUB_API_BASE_URL`
- `LLM_MODEL_RISK`, `LLM_MODEL_KEY_TERMS`, `LLM_MODEL_QA`, `LLM_MODEL_FALLBACK`
- `VISION_MODEL_OCR`
- `LEGAL_RESEARCH_MODEL`
- `EMBEDDING_MODEL_NAME`
- `DATABASE_URL`

Важно:

- Не добавляйте реальные API-ключи в README/docs/commit.
- `text-embedding-3-large` нельзя просто поставить в `EMBEDDING_MODEL_NAME`: текущая реализация использует локальную SentenceTransformer-модель.

## Тесты и сборка

```powershell
pytest backend/tests -q
cd frontend
npm.cmd run build
```

## Manual QA Before Submission

1. DOCX (10–20 страниц): upload → analyze, проверить `risks > 0`, `key_terms > 0`, наличие цитат.
2. PDF с текстовым слоем: upload → analyze, убедиться, что OCR не применялся лишний раз.
3. PDF scan: убедиться, что использован Vision OCR, предупреждения корректны, при плохом скане есть понятное сообщение.
4. Legal sources: либо `sources > 0`, либо понятный empty state; для `model_reported` есть пометка о ручной проверке; нет сырых технических кодов.
5. Q&A: полезный ответ на вопрос по договору и отказ на off-topic вопрос.
6. Reports/Documents: открыть старый отчет, перезагрузить страницу, повторить анализ.

## Ограничения MVP

- Анализ предварительный, не заменяет юриста.
- Качество OCR зависит от качества скана.
- Правовые источники могут требовать ручной проверки.
- Для сложных кейсов нужна дополнительная экспертная валидация.

## Структура проекта

<<<<<<< HEAD
```bash
# 1) Запустить API (Docker или uvicorn)
docker compose up --build

# 2) Установить зависимости для smoke (из корня или backend/)
pip install -r backend/requirements.txt

# 3) Полный прогон (нужен OPENROUTER_API_KEY в backend/.env)
python scripts/smoke_backend.py

# Только инфраструктура без LLM (без ключа — exit code 2)
python scripts/smoke_backend.py --skip-llm
```

Bash-обёртка: `bash scripts/smoke_backend.sh`

Переменные: `SMOKE_BASE_URL`, `OPENROUTER_API_KEY`, `SMOKE_SKIP_LLM=1`, `SMOKE_USERNAME`, `SMOKE_DEMO_FILE`.

Unit-тесты: `cd backend && pytest`

---

# Основной функционал MVP

- Загрузка PDF/DOCX
- OCR обработка
- Извлечение текста
- Анализ рисков
- Генерация отчета
- RAG pipeline
- REST API

---

# Архитектура

Проект использует:
- OCR pipeline
- AI pipeline
- Retrieval-Augmented Generation (RAG)
- LangChain orchestration
- Vector database (ChromaDB)

---

# Команда

## Project Manager / Analyst
- lostsky25

## Backend & AI Developer
- drsail043

## Frontend & QA
- lostsky323

---

# Статус проекта

Проект находится в стадии разработки.

---

# Планируемое развитие

- сравнение договоров;
- рекомендации по исправлению условий;
- мульти-язычность;
- интеграция с CRM;
- расширенный RAG pipeline;
- Agentic RAG
=======
- `backend/app/agents` — agent orchestration и логика анализа.
- `backend/app/services` — OCR, провайдеры, RAG и вспомогательные сервисы.
- `backend/tests` — unit/integration тесты backend.
- `frontend/src/components` — основные UI-компоненты интерфейса.
- `docs` — контракт API, workflow, env и schema-документация.
>>>>>>> 47e1ff0 (global update project)
