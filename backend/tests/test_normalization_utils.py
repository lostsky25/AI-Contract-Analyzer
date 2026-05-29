from app.agents.normalization_utils import (
    canonicalize_url,
    classify_source_type_from_url,
    normalize_quote,
)


def test_quote_cleanup_drops_trailing_fragment() -> None:
    raw = "Payment shall be made within 10 business days and ежемесячное возн"
    cleaned = normalize_quote(raw, max_chars=420, max_sentences=3)
    assert "возн" not in cleaned
    assert cleaned.endswith("and ежемесячное")


def test_quote_cleanup_shortens_long_quote_to_few_sentences() -> None:
    raw = (
        "Sentence one is complete. Sentence two is complete and relevant. "
        "Sentence three is complete as well. Sentence four should not be included."
    )
    cleaned = normalize_quote(raw, max_chars=420, max_sentences=3)
    assert "Sentence four" not in cleaned
    assert cleaned.count(".") <= 3


def test_source_type_normalization_from_domain() -> None:
    assert (
        classify_source_type_from_url("https://www.consultant.ru/document/cons_doc_LAW_123/")
        == "consultant_plus"
    )


def test_canonicalize_url_removes_fragment_and_trailing_slash() -> None:
    assert (
        canonicalize_url("https://www.consultant.ru/document/1/#abc")
        == "https://www.consultant.ru/document/1"
    )
