from pathlib import Path

import fitz
from docx import Document


def _extract_docx_pages(file_path: Path) -> list[dict]:
    document = Document(str(file_path))
    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    text = "\n".join(lines).strip()
    if not text:
        return []
    # DOCX has no reliable page boundaries in this MVP.
    return [{"page": 1, "text": text}]


def _extract_pdf_pages(file_path: Path) -> list[dict]:
    pages: list[dict] = []
    with fitz.open(str(file_path)) as pdf_document:
        for index, page in enumerate(pdf_document, start=1):
            text = (page.get_text() or "").strip()
            if text:
                pages.append({"page": index, "text": text})
    return pages


def extract_pages(file_path: str) -> list[dict]:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".docx":
        return _extract_docx_pages(path)
    if extension == ".pdf":
        return _extract_pdf_pages(path)
    raise ValueError("Unsupported file type. Only .pdf and .docx are supported.")


def extract_text(file_path: str) -> str:
    pages = extract_pages(file_path)
    if not pages:
        return ""
    return "\n\n".join(page["text"] for page in pages if page.get("text")).strip()
