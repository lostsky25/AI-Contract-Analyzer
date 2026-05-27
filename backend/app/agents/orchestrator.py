from sqlalchemy.orm import Session

from app.agents.analysis_agent import AnalysisAgent
from app.agents.document_processing_agent import DocumentProcessingAgent
from app.services.document_repository import update_document_status


class Orchestrator:
    def __init__(self) -> None:
        self.document_processing_agent = DocumentProcessingAgent()
        self.analysis_agent = AnalysisAgent()

    def run(self, db: Session, document_id: str, file_path: str, user_id: str) -> dict:
        update_document_status(
            db=db,
            document_id=document_id,
            status="processing",
            user_id=user_id,
        )
        try:
            processed = self.document_processing_agent.run(document_id, file_path)
            raw = processed["raw"]
            evidence = self.analysis_agent.retrieve_evidence(
                document_id=document_id,
                text=raw["full_text"],
            )
            risk_output = self.analysis_agent.analyze_risks(evidence)
            key_terms = self.analysis_agent.extract_key_terms(evidence)
            report = self.analysis_agent.assemble_report(
                document_id=document_id,
                risk_output=risk_output,
                key_terms=key_terms,
                used_ocr=raw["used_ocr"],
                chunks_count=raw["chunks_count"],
            )
            update_document_status(
                db=db,
                document_id=document_id,
                status="done",
                text_length=raw["text_length"],
                user_id=user_id,
            )
            return report
        except Exception:
            update_document_status(
                db=db,
                document_id=document_id,
                status="failed",
                user_id=user_id,
            )
            raise
