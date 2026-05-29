import pytest

from app.services.chunking_service import chunk_records_from_pages, chunk_text


def test_short_text_returns_one_chunk() -> None:
    chunks = chunk_text("Short contract text.")
    assert len(chunks) == 1
    assert chunks[0] == "Short contract text."


def test_long_text_returns_multiple_chunks() -> None:
    text = "A" * 3000
    chunks = chunk_text(text, chunk_size=1200, overlap=200)
    assert len(chunks) > 1


def test_overlap_greater_or_equal_chunk_size_raises_value_error() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller than chunk_size"):
        chunk_text("example text", chunk_size=200, overlap=200)


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("") == []


def test_chunk_records_from_pages_preserves_page() -> None:
    records = chunk_records_from_pages(
        [
            {"page": 2, "text": "Termination requires 30 days notice."},
            {"page": 5, "text": "Payment terms are net 30."},
        ]
    )
    assert len(records) >= 2
    assert records[0]["page"] == 2
    assert records[0]["chunk_index"] == 0
    assert all(record["page"] == 2 for record in records if "Termination" in record["text"])
