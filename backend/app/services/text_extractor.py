import logging
import re
from pathlib import Path

import fitz
from docx import Document

from app.config import settings
from app.services.ocr_service import run_ocr_image_bytes
from app.services.ocr_text_validation import looks_like_valid_ocr_text
from app.services.provider_errors import ProviderError
from app.services.vision_provider_service import extract_text_from_image_with_vision_provider

logger = logging.getLogger(__name__)
VLM_OCR_INFO_MESSAGE = "INFO: Для распознавания сканированных страниц использован Vision OCR."

FALLBACK_USED_WARNING = "Часть текста была распознана через резервный OCR, возможны ошибки распознавания."
VLM_FAILED_WITH_FALLBACK_WARNING = (
    "Vision OCR не смог надёжно распознать часть страниц. Использован резервный OCR, возможны ошибки."
)
PAGES_SKIPPED_WARNING = "Часть страниц PDF-скана не удалось распознать достаточно качественно."
INSUFFICIENT_OCR_TEXT_WARNING = (
    "Из PDF-скана удалось извлечь недостаточно текста для надёжного анализа. "
    "Проверьте качество скана или используйте файл с текстовым слоем."
)


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


def _resolve_openrouter_vision_base_url() -> str:
    return settings.get_vision_base_url()


def _map_vlm_provider_error_to_warning(error: ProviderError) -> str:
    code = str(error.code)
    legacy = str(error.legacy_code or "")
    if code in {"provider_model_not_found", "openrouter_model_not_found"} or legacy == "openrouter_model_not_found":
        return "Vision OCR модель недоступна, использован резервный OCR."
    if code in {"provider_rate_limited", "openrouter_rate_limited"} or legacy == "openrouter_rate_limited":
        return "Лимит Vision OCR временно исчерпан, использован резервный OCR."
    if code in {"provider_timeout", "openrouter_timeout"} or legacy == "openrouter_timeout":
        return "Vision OCR не ответил вовремя, использован резервный OCR."
    if code in {"provider_auth_failed", "openrouter_auth_failed"} or legacy == "openrouter_auth_failed":
        return "Ошибка доступа к Vision OCR, использован резервный OCR."
    if code in {"provider_unavailable", "openrouter_unavailable"} or legacy == "openrouter_unavailable":
        return "Vision OCR временно недоступен, использован резервный OCR."
    return "Vision OCR завершился с ошибкой, использован резервный OCR."


def _resolve_vlm_configuration() -> tuple[bool, dict[str, str | float | bool], str | None, list[str]]:
    warnings: list[str] = []

    provider = settings.ocr_provider.strip().lower()
    vlm_enabled = provider == "hybrid" and settings.ocr_use_vlm
    if not vlm_enabled:
        return False, {}, "Vision OCR отключен настройками OCR, использован резервный OCR.", warnings

    vision_provider = settings.get_vision_provider()
    if vision_provider == "disabled":
        return False, {}, "Vision OCR отключен, использован резервный OCR.", warnings

    if vision_provider == "bothub":
        api_key = settings.get_vision_api_key()
        model = str(settings.vision_model_ocr or "").strip()
        base_url = settings.get_vision_base_url()
        if not api_key:
            return False, {}, "Не задан ключ Vision OCR, использован резервный OCR.", warnings
        if not model:
            return False, {}, "Не задана модель Vision OCR, использован резервный OCR.", warnings
        return (
            True,
            {
                "provider": "bothub",
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
                "timeout": float(settings.vision_timeout_seconds),
                "include_usage": bool(settings.vision_include_usage),
            },
            None,
            warnings,
        )

    preferred_vlm_model = str(settings.openrouter_model_ocr_vlm or "").strip()
    legacy_vlm_model = str(settings.openrouter_ocr_model or "").strip()
    if preferred_vlm_model:
        model = preferred_vlm_model
    elif legacy_vlm_model:
        model = legacy_vlm_model
        alias_warning = "OPENROUTER_MODEL_OCR_VLM не задан, используется legacy OPENROUTER_OCR_MODEL."
        warnings.append(alias_warning)
        logger.warning(alias_warning)
    else:
        model = ""

    api_key = settings.get_vision_api_key()
    if not api_key:
        return False, {}, "Не задан ключ Vision OCR, использован резервный OCR.", warnings
    if not model:
        return False, {}, "Не задана модель Vision OCR, использован резервный OCR.", warnings

    return (
        True,
        {
            "provider": "openrouter",
            "base_url": _resolve_openrouter_vision_base_url(),
            "api_key": api_key,
            "model": model,
            "timeout": float(settings.vision_timeout_seconds or settings.ocr_vlm_timeout_seconds),
            "include_usage": bool(settings.vision_include_usage),
        },
        None,
        warnings,
    )


def _short_doc(document_id: str | None) -> str:
    raw = str(document_id or "").strip()
    if not raw:
        return "unknown"
    return raw[:8]


def _extract_pdf_pages_hybrid(file_path: Path, *, document_id: str | None = None) -> tuple[list[dict], list[str], bool]:
    pages: list[dict] = []
    warnings: list[str] = []
    used_ocr = False
    used_vlm = False
    used_tesseract = False

    low_quality_pages = 0
    pages_text_layer_used = 0
    pages_vlm_ocr_used = 0
    pages_tesseract_used = 0
    pages_skipped = 0

    vlm_failure_happened = False
    vlm_failure_warning: str | None = None
    vlm_invalid_count = 0

    vlm_available, vision_config, vlm_disabled_warning, config_warnings = _resolve_vlm_configuration()
    warnings.extend(config_warnings)

    with fitz.open(str(file_path)) as pdf_document:
        total_pages = len(pdf_document)
        for index, page in enumerate(pdf_document, start=1):
            text_layer = (page.get_text() or "").strip()
            if text_layer and not _is_low_quality_text(text_layer):
                pages.append({"page": index, "text": text_layer, "source": "text_layer"})
                pages_text_layer_used += 1
                continue

            low_quality_pages += 1
            image_bytes = _render_pdf_page_to_png_bytes(page, settings.ocr_vlm_dpi)

            page_accept_source = ""
            page_rejection_reason = ""
            extracted_content_length = 0

            if vlm_available and index <= settings.ocr_vlm_max_pages:
                try:
                    vlm_text = extract_text_from_image_with_vision_provider(
                        image_bytes=image_bytes,
                        page_number=index,
                        model=str(vision_config["model"]),
                        provider=str(vision_config["provider"]),
                        base_url=str(vision_config["base_url"]),
                        api_key=str(vision_config["api_key"]),
                        timeout=float(vision_config["timeout"]),
                        include_usage=bool(vision_config["include_usage"]),
                    ).strip()
                    extracted_content_length = len(vlm_text)
                    if vlm_text:
                        valid, reason = looks_like_valid_ocr_text(
                            vlm_text,
                            min_chars=int(settings.ocr_min_text_chars_per_page),
                        )
                        if valid:
                            pages.append({"page": index, "text": vlm_text, "source": "vlm_ocr"})
                            used_vlm = True
                            used_ocr = True
                            pages_vlm_ocr_used += 1
                            page_accept_source = "vlm_ocr"
                            if settings.ocr_debug:
                                logger.info(
                                    "ocr_page doc=%s page=%d provider=%s model=%s dpi=%d response_received=true extracted_content_length=%d accepted=true rejection_reason=ok fallback_used=false final_page_text_length=%d",
                                    _short_doc(document_id),
                                    index,
                                    str(vision_config["provider"]),
                                    str(vision_config["model"]),
                                    int(settings.ocr_vlm_dpi),
                                    extracted_content_length,
                                    len(vlm_text),
                                )
                            continue
                        vlm_invalid_count += 1
                        page_rejection_reason = f"vlm_invalid_{reason}"
                    else:
                        vlm_invalid_count += 1
                        page_rejection_reason = "vlm_invalid_empty"
                except ProviderError as exc:
                    vlm_failure_happened = True
                    vlm_failure_warning = _map_vlm_provider_error_to_warning(exc)
                    page_rejection_reason = f"vlm_error_{exc.code}"
                    if exc.code in {"provider_model_not_found", "provider_auth_failed"}:
                        vlm_available = False
                except Exception:
                    vlm_failure_happened = True
                    vlm_failure_warning = "Vision OCR завершился с ошибкой, использован резервный OCR."
                    page_rejection_reason = "vlm_error_exception"

            try:
                tesseract_text = run_ocr_image_bytes(image_bytes).strip()
            except Exception:
                tesseract_text = ""

            if tesseract_text:
                valid_tesseract, tesseract_reason = looks_like_valid_ocr_text(
                    tesseract_text,
                    min_chars=max(20, int(settings.ocr_min_text_chars_per_page) // 2),
                )
                if valid_tesseract:
                    pages.append({"page": index, "text": tesseract_text, "source": "tesseract"})
                    used_tesseract = True
                    used_ocr = True
                    pages_tesseract_used += 1
                    page_accept_source = "tesseract"
                else:
                    page_rejection_reason = page_rejection_reason or f"tesseract_invalid_{tesseract_reason}"

            if not page_accept_source:
                if text_layer:
                    pages.append({"page": index, "text": text_layer, "source": "text_layer_fallback"})
                    pages_text_layer_used += 1
                    page_accept_source = "text_layer_fallback"
                else:
                    pages_skipped += 1

            if settings.ocr_debug:
                logger.info(
                    "ocr_page doc=%s page=%d provider=%s model=%s dpi=%d response_received=%s extracted_content_length=%d accepted=%s rejection_reason=%s fallback_used=%s final_page_text_length=%d",
                    _short_doc(document_id),
                    index,
                    str(vision_config.get("provider", "disabled") if vision_config else "disabled"),
                    str(vision_config.get("model", "") if vision_config else ""),
                    int(settings.ocr_vlm_dpi),
                    str(bool(vlm_available and index <= settings.ocr_vlm_max_pages)).lower(),
                    extracted_content_length,
                    str(bool(page_accept_source)).lower(),
                    page_rejection_reason or "none",
                    str(page_accept_source == "tesseract").lower(),
                    len(tesseract_text if page_accept_source == "tesseract" else text_layer or ""),
                )

        if vlm_available and total_pages > settings.ocr_vlm_max_pages:
            warnings.append(
                f"Vision OCR обработал только первые {settings.ocr_vlm_max_pages} страниц из {total_pages}."
            )

    if used_vlm:
        warnings.append(VLM_OCR_INFO_MESSAGE)

    if low_quality_pages > 0 and vlm_disabled_warning:
        warnings.append(vlm_disabled_warning)
    elif low_quality_pages > 0 and (vlm_failure_happened or vlm_invalid_count > 0):
        warnings.append(vlm_failure_warning or VLM_FAILED_WITH_FALLBACK_WARNING)

    if used_tesseract:
        warnings.append(FALLBACK_USED_WARNING)
    if pages_skipped > 0:
        warnings.append(PAGES_SKIPPED_WARNING)

    full_text = "\n\n".join(page.get("text", "") for page in pages if page.get("text"))
    if (
        low_quality_pages > 0
        and len(full_text) < max(200, settings.ocr_min_text_chars_per_page * 4)
        and (pages_skipped > 0 or (pages_vlm_ocr_used + pages_tesseract_used) == 0)
    ):
        warnings.append(INSUFFICIENT_OCR_TEXT_WARNING)

    deduped_warnings: list[str] = []
    seen_warnings: set[str] = set()
    for warning in warnings:
        key = str(warning or "").strip().lower()
        if not key or key in seen_warnings:
            continue
        seen_warnings.add(key)
        deduped_warnings.append(str(warning).strip())

    logger.info(
        "ocr_summary doc=%s total_pages=%d pages_text_layer_used=%d pages_vlm_ocr_used=%d pages_tesseract_used=%d pages_skipped=%d final_text_length=%d warnings_count=%d",
        _short_doc(document_id),
        len(pages) + pages_skipped,
        pages_text_layer_used,
        pages_vlm_ocr_used,
        pages_tesseract_used,
        pages_skipped,
        len(full_text),
        len(deduped_warnings),
    )

    return pages, deduped_warnings, used_ocr


def extract_pages_with_metadata(file_path: str, *, document_id: str | None = None) -> dict:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".docx":
        pages = _extract_docx_pages(path)
        return {"pages": pages, "warnings": [], "used_ocr": False}

    if extension == ".pdf":
        pages, warnings, used_ocr = _extract_pdf_pages_hybrid(path, document_id=document_id)
        return {"pages": pages, "warnings": warnings, "used_ocr": used_ocr}

    raise ValueError("Unsupported file type. Only .pdf and .docx are supported.")


def extract_pages(file_path: str) -> list[dict]:
    return list(extract_pages_with_metadata(file_path).get("pages", []))


def extract_text(file_path: str) -> str:
    pages = extract_pages(file_path)
    if not pages:
        return ""
    return "\n\n".join(page["text"] for page in pages if page.get("text")).strip()
