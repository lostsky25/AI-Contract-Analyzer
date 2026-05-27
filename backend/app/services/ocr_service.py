from pathlib import Path

from app.config import settings

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _configure_tesseract(pytesseract_module: object) -> None:
    if settings.tesseract_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _extract_pdf_with_ocr(path: Path) -> str:
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
        page_texts = [pytesseract.image_to_string(image) for image in images]
        return "\n".join(page_texts).strip()
    except Exception as exc:
        raise RuntimeError(
            "OCR execution failed. Verify TESSERACT_CMD and POPPLER_PATH configuration."
        ) from exc


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
            return pytesseract.image_to_string(image).strip()
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
