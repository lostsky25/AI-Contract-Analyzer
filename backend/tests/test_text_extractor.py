from pathlib import Path

import pytest
from docx import Document

from app.services.text_extractor import extract_text


def test_extract_text_from_docx(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.docx"
    document = Document()
    document.add_paragraph("Payment terms are net 30.")
    document.add_paragraph("Termination requires 30 days notice.")
    document.save(str(file_path))

    extracted = extract_text(str(file_path))
    assert "Payment terms are net 30." in extracted
    assert "Termination requires 30 days notice." in extracted


def test_extract_text_unsupported_extension_raises_value_error(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.txt"
    file_path.write_text("plain text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(str(file_path))
