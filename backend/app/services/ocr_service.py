from pathlib import Path
from io import BytesIO
import logging

from app.config import settings

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
logger = logging.getLogger(__name__)


def _configure_tesseract(pytesseract_module: object) -> None:
    if settings.tesseract_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _resolve_tesseract_lang() -> str:
    lang = str(settings.ocr_tesseract_lang or "").strip()
    return lang or "rus+eng"


def _ocr_image_to_string(pytesseract_module: object, image: object) -> str:
    lang = _resolve_tesseract_lang()
    try:
        return pytesseract_module.image_to_string(image, lang=lang).strip()
    except Exception as exc:
        message = str(exc).lower()
        if "failed loading language" in message or "tessdata" in message:
            logger.warning(
                "Tesseract language '%s' is unavailable; falling back to eng.",
                lang,
            )
            return pytesseract_module.image_to_string(image, lang="eng").strip()
        raise


def run_ocr_pages(file_path: str) -> list[dict]:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        try:
            import pytesseract
            from pdf2image import convert_from_path
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "OCR dependencies are missing. Install pytesseract and pdf2image."
            ) from exc

        _configure_tesseract(pytesseract)
        try:
            images = convert_from_path(
                str(path),
                dpi=300,
                poppler_path=settings.poppler_path or None,
            )
            pages: list[dict] = []
            for index, image in enumerate(images, start=1):
                text = _ocr_image_to_string(pytesseract, image)
                if text:
                    pages.append({"page": index, "text": text})
            return pages
        except Exception as exc:
            raise RuntimeError(
                "OCR execution failed. Verify TESSERACT_CMD and POPPLER_PATH configuration."
            ) from exc

    text = run_ocr(file_path)
    if not text:
        return []
    return [{"page": 1, "text": text}]


def _extract_pdf_with_ocr(path: Path) -> str:
    pages = run_ocr_pages(str(path))
    return "\n\n".join(page["text"] for page in pages).strip()


def _extract_image_with_ocr(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OCR dependencies are missing. Install pytesseract and pillow."
        ) from exc

    _configure_tesseract(pytesseract)
    try:
        with Image.open(path) as image:
            return _ocr_image_to_string(pytesseract, image)
    except Exception as exc:
        raise RuntimeError(
            "OCR execution failed. Verify TESSERACT_CMD configuration."
        ) from exc


def run_ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OCR dependencies are missing. Install pytesseract and pillow."
        ) from exc

    _configure_tesseract(pytesseract)
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return _ocr_image_to_string(pytesseract, image)
    except Exception as exc:
        raise RuntimeError(
            "OCR execution failed. Verify TESSERACT_CMD configuration."
        ) from exc


def run_ocr(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        return _extract_pdf_with_ocr(path)
    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return _extract_image_with_ocr(path)

    raise ValueError("Unsupported OCR file type. Use .pdf, .png, .jpg, or .jpeg.")
