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
