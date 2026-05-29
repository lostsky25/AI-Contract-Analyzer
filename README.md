# AI Contract Analyzer

AI Contract Analyzer — сервис для предварительного анализа шаблонных договоров с использованием OCR, RAG и LLM.

## Цель проекта

Система помогает:
- извлекать текст из PDF/DOCX;
- распознавать сканы через OCR;
- находить потенциальные риски;
- выделять ключевые условия;
- формировать структурированный отчет.

Важно:
> Проект не заменяет юриста и используется как инструмент предварительного анализа документов.
---

# Стек

## Backend
- Python 3.12
- FastAPI

## Frontend
- React
- TailwindCSS

## AI
- OpenRouter API
- LangChain
- RAG

## OCR
- Tesseract OCR
- PyMuPDF
- python-docx

## Database
- PostgreSQL
- ChromaDB

## DevOps
- Docker
- GitHub

---

# Быстрый старт (Docker)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Укажите `OPENROUTER_API_KEY` в `backend/.env`. Подробнее: [docs/env-setup.md](docs/env-setup.md).

API: http://localhost:8000/docs

Подробнее: [backend/README.md](backend/README.md)

## Smoke test (agent workflow)

Проверяет живой API: health, upload, analyze (LegalResearchAgent), report, Q&A.

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
- Agentic RAG.
