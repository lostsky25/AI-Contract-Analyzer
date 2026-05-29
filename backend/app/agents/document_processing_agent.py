from app.services.document_processor import process_document


class DocumentProcessingAgent:
    def run(self, document_id: str, file_path: str) -> dict:
        result = process_document(document_id, file_path)
        return {
            "document_id": document_id,
            "pages": result.get("pages", []),
            "metadata": {
                "file_type": file_path.split(".")[-1].lower(),
                "ocr_used": result["used_ocr"],
            },
            "raw": result,
        }
