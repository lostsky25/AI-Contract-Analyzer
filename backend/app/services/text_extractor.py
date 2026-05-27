from pathlib import Path

import fitz
from docx import Document


def _extract_docx_text(file_path: Path) -> str:
    document = Document(str(file_path))
    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    return "\n".join(lines).strip()


def _extract_pdf_text(file_path: Path) -> str:
    chunks: list[str] = []
    with fitz.open(str(file_path)) as pdf_document:
        for page in pdf_document:
            chunks.append(page.get_text() or "")
    return "\n".join(chunks).strip()


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".docx":
        extracted_text = _extract_docx_text(path)
    elif extension == ".pdf":
        extracted_text = _extract_pdf_text(path)
    else:
        raise ValueError("Unsupported file type. Only .pdf and .docx are supported.")

    if not extracted_text:
        return ""

    return extracted_text
