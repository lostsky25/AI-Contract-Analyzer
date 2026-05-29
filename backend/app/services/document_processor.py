import re
from pathlib import Path

from app.services.chunking_service import chunk_records_from_pages
from app.services.ocr_service import run_ocr, run_ocr_pages
from app.services.text_extractor import extract_pages


def _clean_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def process_document(document_id: str, file_path: str) -> dict:
    path = Path(file_path)
    pages = extract_pages(file_path)
    used_ocr = False

    if not any(str(page.get("text", "")).strip() for page in pages):
        if path.suffix.lower() == ".pdf":
            pages = run_ocr_pages(file_path)
        else:
            ocr_text = run_ocr(file_path)
            pages = [{"page": 1, "text": ocr_text}] if ocr_text else []
        used_ocr = True

    pages = [
        {"page": page.get("page"), "text": _clean_text(str(page.get("text", "")))}
        for page in pages
        if str(page.get("text", "")).strip()
    ]

    chunk_records = chunk_records_from_pages(pages)
    for index, record in enumerate(chunk_records):
        record["chunk_id"] = f"{document_id}_{index}"

    full_text = "\n\n".join(page["text"] for page in pages)
    chunks = [record["text"] for record in chunk_records]
    text_length = len(full_text)
    status = "processed" if text_length > 0 else "empty_text"

    return {
        "document_id": document_id,
        "status": status,
        "text_preview": full_text[:1000],
        "full_text": full_text,
        "text_length": text_length,
        "chunks_count": len(chunk_records),
        "chunks": chunks,
        "chunk_records": chunk_records,
        "pages": pages,
        "used_ocr": used_ocr,
    }
