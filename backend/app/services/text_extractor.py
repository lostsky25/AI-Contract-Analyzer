import logging
import re
from pathlib import Path

import fitz
from docx import Document

from app.config import settings
from app.services.llm_service import extract_text_from_image_with_vlm
from app.services.openrouter_service import ProviderError
from app.services.ocr_service import run_ocr_image_bytes

logger = logging.getLogger(__name__)
VLM_OCR_INFO_MESSAGE = "INFO: Для части страниц использовано VLM-распознавание текста."


def _extract_docx_pages(file_path: Path) -> list[dict]:
    document = Document(str(file_path))
    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    text = "\n".join(lines).strip()
    if not text:
        return []
    # DOCX has no reliable page boundaries in this MVP.
    return [{"page": 1, "text": text, "source": "docx"}]


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned


def _is_low_quality_text(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if len(normalized) < settings.ocr_min_text_chars_per_page:
        return True

    words = re.findall(r"\b[\w-]+\b", normalized, flags=re.UNICODE)
    if len(words) < 6:
        return True

    letters = [char for char in normalized if char.isalpha()]
    if not letters:
        return True

    cyrillic_count = sum(1 for char in letters if re.match(r"[А-Яа-яЁё]", char))
    latin_count = sum(1 for char in letters if "a" <= char.lower() <= "z")
    if cyrillic_count > 0 and latin_count > cyrillic_count * 2:
        return True

    allowed_punct = set(',.;:!?()[]{}"\'/-%№')
    noisy_symbols = sum(
        1
        for char in normalized
        if not (char.isalnum() or char.isspace() or char in allowed_punct)
    )
    if noisy_symbols / max(1, len(normalized)) > 0.2:
        return True

    return False


def _render_pdf_page_to_png_bytes(page: fitz.Page, dpi: int) -> bytes:
    scale = max(1, dpi) / 72.0
    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return pixmap.tobytes("png")


def _resolve_vlm_configuration() -> tuple[bool, str, str | None, list[str]]:
    warnings: list[str] = []

    provider = settings.ocr_provider.strip().lower()
    vlm_enabled = provider == "hybrid" and settings.ocr_use_vlm

    preferred_vlm_model = str(settings.openrouter_model_ocr_vlm or "").strip()
    legacy_vlm_model = str(settings.openrouter_ocr_model or "").strip()
    has_api_key = bool((settings.openrouter_api_key or "").strip())

    if preferred_vlm_model:
        model = preferred_vlm_model
    elif legacy_vlm_model:
        model = legacy_vlm_model
        alias_warning = (
            "OPENROUTER_MODEL_OCR_VLM is not set; using legacy OPENROUTER_OCR_MODEL."
        )
        warnings.append(alias_warning)
        logger.warning(alias_warning)
    else:
        model = ""

    if not vlm_enabled:
        return False, model, "VLM OCR is disabled by OCR settings; used local OCR fallback.", warnings
    if not has_api_key:
        return False, model, "OpenRouter API key is missing; used local OCR fallback.", warnings
    if not model:
        return False, model, "VLM OCR model is not configured; used local OCR fallback.", warnings

    return True, model, None, warnings


def _extract_pdf_pages_hybrid(file_path: Path) -> tuple[list[dict], list[str], bool]:
    pages: list[dict] = []
    warnings: list[str] = []
    used_ocr = False
    used_vlm = False
    used_tesseract = False
    low_quality_pages = 0
    vlm_failure_happened = False
    vlm_failure_warning: str | None = None

    vlm_available, vlm_model, vlm_disabled_warning, config_warnings = _resolve_vlm_configuration()
    warnings.extend(config_warnings)

    with fitz.open(str(file_path)) as pdf_document:
        total_pages = len(pdf_document)
        for index, page in enumerate(pdf_document, start=1):
            text_layer = (page.get_text() or "").strip()
            if text_layer and not _is_low_quality_text(text_layer):
                pages.append({"page": index, "text": text_layer, "source": "text_layer"})
                continue

            low_quality_pages += 1
            image_bytes = _render_pdf_page_to_png_bytes(page, settings.ocr_vlm_dpi)

            if vlm_available and index <= settings.ocr_vlm_max_pages:
                try:
                    vlm_text = extract_text_from_image_with_vlm(
                        image_bytes=image_bytes,
                        page_number=index,
                        model=vlm_model,
                    ).strip()
                    if vlm_text:
                        pages.append({"page": index, "text": vlm_text, "source": "vlm_ocr"})
                        used_vlm = True
                        used_ocr = True
                        continue
                except ProviderError as exc:
                    vlm_failure_happened = True
                    if exc.code == "openrouter_model_not_found":
                        vlm_failure_warning = (
                            "VLM OCR model is unavailable in OpenRouter; used local OCR fallback."
                        )
                        # Avoid repeated failing calls on next pages.
                        vlm_available = False
                    elif exc.code == "openrouter_rate_limited":
                        vlm_failure_warning = (
                            "VLM OCR rate limit exceeded; used local OCR fallback."
                        )
                    elif exc.code == "openrouter_timeout":
                        vlm_failure_warning = "VLM OCR timed out; used local OCR fallback."
                    else:
                        vlm_failure_warning = "VLM OCR request failed; used local OCR fallback."
                except Exception:
                    vlm_failure_happened = True
                    vlm_failure_warning = "VLM OCR request failed; used local OCR fallback."

            try:
                tesseract_text = run_ocr_image_bytes(image_bytes).strip()
            except Exception:
                tesseract_text = ""

            if tesseract_text:
                pages.append({"page": index, "text": tesseract_text, "source": "tesseract"})
                used_tesseract = True
                used_ocr = True
                continue

            if text_layer:
                pages.append({"page": index, "text": text_layer, "source": "text_layer"})

        if vlm_available and total_pages > settings.ocr_vlm_max_pages:
            warnings.append(
                f"VLM OCR processed only first {settings.ocr_vlm_max_pages} pages out of {total_pages}."
            )

    if used_vlm:
        warnings.append(VLM_OCR_INFO_MESSAGE)

    if low_quality_pages > 0 and vlm_disabled_warning:
        warnings.append(vlm_disabled_warning)
    elif low_quality_pages > 0 and vlm_failure_happened:
        warnings.append(vlm_failure_warning or "VLM OCR request failed; used local OCR fallback.")

    if low_quality_pages > 0 and used_tesseract:
        warnings.append("Использовано локальное OCR. Качество может быть ниже.")

    return pages, warnings, used_ocr


def extract_pages_with_metadata(file_path: str) -> dict:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".docx":
        pages = _extract_docx_pages(path)
        return {"pages": pages, "warnings": [], "used_ocr": False}

    if extension == ".pdf":
        pages, warnings, used_ocr = _extract_pdf_pages_hybrid(path)
        return {"pages": pages, "warnings": warnings, "used_ocr": used_ocr}

    raise ValueError("Unsupported file type. Only .pdf and .docx are supported.")


def extract_pages(file_path: str) -> list[dict]:
    return list(extract_pages_with_metadata(file_path).get("pages", []))


def extract_text(file_path: str) -> str:
    pages = extract_pages(file_path)
    if not pages:
        return ""
    return "\n\n".join(page["text"] for page in pages if page.get("text")).strip()
