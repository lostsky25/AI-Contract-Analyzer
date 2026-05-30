from pathlib import Path
import sys
import types

import pytest
from docx import Document

from app.config import settings
from app.services import ocr_service, text_extractor
from app.services.openrouter_service import ProviderError
from app.services.text_extractor import (
    VLM_OCR_INFO_MESSAGE,
    extract_pages,
    extract_pages_with_metadata,
    extract_text,
)


class _FakePdfPage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _FakePdfDocument:
    def __init__(self, page_texts: list[str]) -> None:
        self._pages = [_FakePdfPage(text) for text in page_texts]

    def __iter__(self):
        return iter(self._pages)

    def __len__(self) -> int:
        return len(self._pages)

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False


@pytest.fixture(autouse=True)
def reset_ocr_settings():
    snapshot = {
        "ocr_provider": settings.ocr_provider,
        "ocr_use_vlm": settings.ocr_use_vlm,
        "openrouter_api_key": settings.openrouter_api_key,
        "openrouter_model_ocr_vlm": settings.openrouter_model_ocr_vlm,
        "openrouter_ocr_model": settings.openrouter_ocr_model,
        "ocr_min_text_chars_per_page": settings.ocr_min_text_chars_per_page,
        "ocr_vlm_max_pages": settings.ocr_vlm_max_pages,
        "ocr_tesseract_lang": settings.ocr_tesseract_lang,
    }
    yield
    settings.ocr_provider = snapshot["ocr_provider"]
    settings.ocr_use_vlm = snapshot["ocr_use_vlm"]
    settings.openrouter_api_key = snapshot["openrouter_api_key"]
    settings.openrouter_model_ocr_vlm = snapshot["openrouter_model_ocr_vlm"]
    settings.openrouter_ocr_model = snapshot["openrouter_ocr_model"]
    settings.ocr_min_text_chars_per_page = snapshot["ocr_min_text_chars_per_page"]
    settings.ocr_vlm_max_pages = snapshot["ocr_vlm_max_pages"]
    settings.ocr_tesseract_lang = snapshot["ocr_tesseract_lang"]


def test_extract_text_from_docx(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.docx"
    document = Document()
    document.add_paragraph("Payment terms are net 30.")
    document.add_paragraph("Termination requires 30 days notice.")
    document.save(str(file_path))

    extracted = extract_text(str(file_path))
    assert "Payment terms are net 30." in extracted
    assert "Termination requires 30 days notice." in extracted


def test_docx_extraction_does_not_call_vlm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "contract.docx"
    document = Document()
    document.add_paragraph("Clause on page one.")
    document.save(str(file_path))

    monkeypatch.setattr(
        text_extractor,
        "extract_text_from_image_with_vlm",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("VLM must not be used for DOCX")),
    )

    result = extract_pages_with_metadata(str(file_path))
    assert result["used_ocr"] is False
    assert result["pages"][0]["source"] == "docx"


def test_pdf_with_good_text_layer_skips_vlm(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_min_text_chars_per_page = 10
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = "dummy-model"

    monkeypatch.setattr(
        text_extractor.fitz,
        "open",
        lambda _path: _FakePdfDocument(
            ["Настоящий договор устанавливает сроки оплаты и порядок расторжения сторонами."]
        ),
    )
    monkeypatch.setattr(
        text_extractor,
        "extract_text_from_image_with_vlm",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("VLM must not be called")),
    )

    result = extract_pages_with_metadata("dummy.pdf")
    assert result["used_ocr"] is False
    assert result["warnings"] == []
    assert result["pages"][0]["source"] == "text_layer"


def test_scanned_pdf_uses_vlm_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = "dummy-model"
    settings.ocr_vlm_max_pages = 20
    settings.ocr_min_text_chars_per_page = 50

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")
    monkeypatch.setattr(
        text_extractor,
        "extract_text_from_image_with_vlm",
        lambda **_kwargs: "Оплата производится в течение 10 банковских дней.",
    )
    monkeypatch.setattr(
        text_extractor,
        "run_ocr_image_bytes",
        lambda _image_bytes: (_ for _ in ()).throw(AssertionError("Tesseract should not be used when VLM succeeds")),
    )

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["used_ocr"] is True
    assert result["pages"][0]["source"] == "vlm_ocr"
    assert VLM_OCR_INFO_MESSAGE in result["warnings"]
    assert not any("Качество распознавания текста может быть снижено." in warning for warning in result["warnings"])


def test_vlm_model_missing_falls_back_to_tesseract_without_openrouter_call(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = ""
    settings.openrouter_ocr_model = ""

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")
    monkeypatch.setattr(
        text_extractor,
        "extract_text_from_image_with_vlm",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("VLM must not be called when model is missing")),
    )
    monkeypatch.setattr(text_extractor, "run_ocr_image_bytes", lambda _image_bytes: "Fallback tesseract text")

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["pages"][0]["source"] == "tesseract"
    assert any("model is not configured" in warning for warning in result["warnings"])


def test_vlm_model_not_found_falls_back_to_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = "missing-model"

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")

    def _raise_not_found(**_kwargs):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_model_not_found",
            message="model not found",
            retryable=False,
        )

    monkeypatch.setattr(text_extractor, "extract_text_from_image_with_vlm", _raise_not_found)
    monkeypatch.setattr(text_extractor, "run_ocr_image_bytes", lambda _image_bytes: "Fallback tesseract text")

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["pages"][0]["source"] == "tesseract"
    assert any("model is unavailable" in warning for warning in result["warnings"])


def test_vlm_rate_limited_falls_back_to_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = "rate-limited-model"

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")

    def _raise_429(**_kwargs):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_rate_limited",
            message="rate limited",
            retryable=True,
        )

    monkeypatch.setattr(text_extractor, "extract_text_from_image_with_vlm", _raise_429)
    monkeypatch.setattr(text_extractor, "run_ocr_image_bytes", lambda _image_bytes: "Fallback tesseract text")

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["pages"][0]["source"] == "tesseract"
    assert any("rate limit" in warning for warning in result["warnings"])


def test_vlm_timeout_falls_back_to_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = "dummy"
    settings.openrouter_model_ocr_vlm = "slow-model"

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")

    def _raise_timeout(**_kwargs):
        raise ProviderError(
            provider="openrouter",
            code="openrouter_timeout",
            message="timeout",
            retryable=True,
        )

    monkeypatch.setattr(text_extractor, "extract_text_from_image_with_vlm", _raise_timeout)
    monkeypatch.setattr(text_extractor, "run_ocr_image_bytes", lambda _image_bytes: "Fallback tesseract text")

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["pages"][0]["source"] == "tesseract"
    assert any("timed out" in warning for warning in result["warnings"])


def test_without_openrouter_key_uses_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.ocr_provider = "hybrid"
    settings.ocr_use_vlm = True
    settings.openrouter_api_key = ""
    settings.openrouter_model_ocr_vlm = "dummy-model"

    monkeypatch.setattr(text_extractor.fitz, "open", lambda _path: _FakePdfDocument([""]))
    monkeypatch.setattr(text_extractor, "_render_pdf_page_to_png_bytes", lambda _page, _dpi: b"png")
    monkeypatch.setattr(
        text_extractor,
        "extract_text_from_image_with_vlm",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("VLM must not be called without API key")),
    )
    monkeypatch.setattr(text_extractor, "run_ocr_image_bytes", lambda _image_bytes: "Fallback text from tesseract.")

    result = extract_pages_with_metadata("scanned.pdf")
    assert result["pages"][0]["source"] == "tesseract"
    assert any("API key is missing" in warning for warning in result["warnings"])


def test_extract_pages_from_docx_uses_single_page(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.docx"
    document = Document()
    document.add_paragraph("Clause on page one.")
    document.save(str(file_path))

    pages = extract_pages(str(file_path))
    assert len(pages) == 1
    assert pages[0]["page"] == 1
    assert pages[0]["source"] == "docx"
    assert "Clause on page one." in pages[0]["text"]


def test_extract_text_unsupported_extension_raises_value_error(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.txt"
    file_path.write_text("plain text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(str(file_path))


def test_run_ocr_image_bytes_uses_default_rus_plus_eng_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class _DummyImage:
        def __enter__(self):
            return object()

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    class _PytesseractInner:
        tesseract_cmd = ""

    def _image_to_string(_img, lang=None):
        captured["lang"] = str(lang or "")
        return "ok"

    pytesseract_module = types.ModuleType("pytesseract")
    pytesseract_module.pytesseract = _PytesseractInner()
    pytesseract_module.image_to_string = _image_to_string

    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = lambda _stream: _DummyImage()
    pil_module = types.ModuleType("PIL")
    pil_module.Image = pil_image_module

    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract_module)
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image_module)

    settings.ocr_tesseract_lang = "rus+eng"
    result = ocr_service.run_ocr_image_bytes(b"fake")

    assert captured["lang"] == "rus+eng"
    assert result == "ok"


def test_run_ocr_image_bytes_falls_back_to_eng_when_lang_pack_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class _DummyImage:
        def __enter__(self):
            return object()

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    class _PytesseractInner:
        tesseract_cmd = ""

    def _image_to_string(_img, lang=None):
        calls.append(str(lang or ""))
        if lang == "rus+eng":
            raise RuntimeError("Failed loading language 'rus+eng'")
        return "english-fallback-ok"

    pytesseract_module = types.ModuleType("pytesseract")
    pytesseract_module.pytesseract = _PytesseractInner()
    pytesseract_module.image_to_string = _image_to_string

    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = lambda _stream: _DummyImage()
    pil_module = types.ModuleType("PIL")
    pil_module.Image = pil_image_module

    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract_module)
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image_module)

    settings.ocr_tesseract_lang = "rus+eng"
    result = ocr_service.run_ocr_image_bytes(b"fake")

    assert calls == ["rus+eng", "eng"]
    assert result == "english-fallback-ok"
