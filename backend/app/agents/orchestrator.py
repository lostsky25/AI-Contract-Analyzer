from sqlalchemy.orm import Session

from app.agents.analysis_agent import AnalysisAgent
from app.agents.document_processing_agent import DocumentProcessingAgent
<<<<<<< HEAD
=======
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.report_agent import ReportAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.services.report_store import save_report
>>>>>>> feature/backend-mvp
from app.services.document_repository import update_document_status


class Orchestrator:
    def __init__(self) -> None:
        self.document_processing_agent = DocumentProcessingAgent()
<<<<<<< HEAD
        self.analysis_agent = AnalysisAgent()
=======
        self.retrieval_agent = RetrievalAgent()
        self.analysis_agent = AnalysisAgent()
        self.legal_research_agent = LegalResearchAgent()
        self.report_agent = ReportAgent()
>>>>>>> feature/backend-mvp

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
<<<<<<< HEAD
            evidence = self.analysis_agent.retrieve_evidence(
                document_id=document_id,
                text=raw["full_text"],
            )
            risk_output = self.analysis_agent.analyze_risks(evidence)
            key_terms = self.analysis_agent.extract_key_terms(evidence)
            report = self.analysis_agent.assemble_report(
=======
            retrieval = self.retrieval_agent.run(document_id=document_id, text=raw["full_text"])
            merged_context = retrieval.get("risk_context", []) + retrieval.get("terms_context", [])
            risk_output = self.analysis_agent.analyze_risks(merged_context)
            key_terms = self.analysis_agent.extract_key_terms(retrieval.get("terms_context", []))
            legal_research = self.legal_research_agent.run(
                query=str(risk_output.get("summary", "")) or raw["text_preview"]
            )
            assembled = self.analysis_agent.assemble_report(
>>>>>>> feature/backend-mvp
                document_id=document_id,
                risk_output=risk_output,
                key_terms=key_terms,
                used_ocr=raw["used_ocr"],
<<<<<<< HEAD
                chunks_count=raw["chunks_count"],
            )
=======
                chunks_count=retrieval.get("chunks_count", raw["chunks_count"]),
            )
            assembled["legal_sources"] = legal_research.get("legal_sources", [])
            assembled["warnings"] = legal_research.get("warnings", [])
            report = self.report_agent.run(assembled)
            save_report(document_id, report)
>>>>>>> feature/backend-mvp
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
