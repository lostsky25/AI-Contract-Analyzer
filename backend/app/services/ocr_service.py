from pathlib import Path
from io import BytesIO

from app.config import settings

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _configure_tesseract(pytesseract_module: object) -> None:
    if settings.tesseract_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = settings.tesseract_cmd


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
                text = pytesseract.image_to_string(image).strip()
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
            return pytesseract.image_to_string(image).strip()
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
