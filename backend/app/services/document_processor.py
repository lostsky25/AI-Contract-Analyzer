import re

from app.services.chunking_service import chunk_text
from app.services.ocr_service import run_ocr
from app.services.text_extractor import extract_text


def _clean_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def process_document(document_id: str, file_path: str) -> dict:
    extracted_text = extract_text(file_path)
    used_ocr = False

    if not extracted_text:
        extracted_text = run_ocr(file_path)
        used_ocr = True

    cleaned_text = _clean_text(extracted_text)
    text_length = len(cleaned_text)
    status = "processed" if text_length > 0 else "empty_text"
    chunks = chunk_text(cleaned_text) if cleaned_text else []

    return {
        "document_id": document_id,
        "status": status,
        "text_preview": cleaned_text[:1000],
        "text_length": text_length,
        "chunks_count": len(chunks),
        "used_ocr": used_ocr,
    }
