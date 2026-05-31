import logging

from sqlalchemy.orm import Session

from app.agents.analysis_agent import AnalysisAgent
from app.agents.document_processing_agent import DocumentProcessingAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.report_agent import ReportAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.services.document_repository import update_document_status
from app.services.report_store import save_report

INFO_WARNING_PREFIX = "INFO:"
logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self) -> None:
        self.document_processing_agent = DocumentProcessingAgent()
        self.retrieval_agent = RetrievalAgent()
        self.analysis_agent = AnalysisAgent()
        self.legal_research_agent = LegalResearchAgent()
        self.report_agent = ReportAgent()

    def run(
        self,
        db: Session,
        document_id: str,
        file_path: str,
        user_id: str,
        legal_web_search_enabled: bool = True,
    ) -> dict:
        update_document_status(
            db=db,
            document_id=document_id,
            status="processing",
            user_id=user_id,
        )
        try:
            processed = self.document_processing_agent.run(document_id, file_path)
            raw = processed["raw"]
            retrieval = self.retrieval_agent.run(
                document_id=document_id,
                text=raw["full_text"],
                chunk_records=raw.get("chunk_records"),
                pages=raw.get("pages"),
            )
            merged_context = retrieval.get("risk_context", []) + retrieval.get(
                "terms_context", []
            )
            risk_output = self.analysis_agent.analyze_risks(merged_context)
            if hasattr(self.analysis_agent, "extract_key_terms_with_grounding"):
                key_terms_result = self.analysis_agent.extract_key_terms_with_grounding(
                    retrieval.get("terms_context", [])
                )
                key_terms = list(key_terms_result.get("key_terms", []))
                key_terms_warnings = list(key_terms_result.get("warnings", []))
            else:
                key_terms = self.analysis_agent.extract_key_terms(
                    retrieval.get("terms_context", [])
                )
                key_terms_warnings = []

            risks = list(risk_output.get("risks", []))
            analysis_warnings = list(risk_output.get("warnings", []))
            summary = str(risk_output.get("summary", "")) or raw.get("text_preview", "")
            legal_research: dict = {"legal_sources": [], "warnings": []}
            try:
                legal_research = self.legal_research_agent.run(
                    document_id=document_id,
                    risks=risks,
                    key_terms=key_terms,
                    summary=summary,
                    web_search_enabled=legal_web_search_enabled,
                )
            except Exception:
                legal_research = {
                    "legal_sources": [],
                    "warnings": ["Проверка публичных правовых источников выполнена с ограничениями."],
                }
            assembled = self.analysis_agent.assemble_report(
                document_id=document_id,
                risk_output=risk_output,
                key_terms=key_terms,
                used_ocr=raw["used_ocr"],
                chunks_count=retrieval.get("chunks_count", raw["chunks_count"]),
            )
            assembled["legal_sources"] = legal_research.get("legal_sources", [])
            process_warnings = list(raw.get("warnings", []))
            retrieval_warnings = list(retrieval.get("warnings", []))
            legal_warnings = list(legal_research.get("warnings", []))
            merged_warnings = list(
                dict.fromkeys(
                    process_warnings
                    + retrieval_warnings
                    + analysis_warnings
                    + key_terms_warnings
                    + legal_warnings
                )
            )
            actionable_warnings = [
                warning
                for warning in merged_warnings
                if not str(warning).strip().startswith(INFO_WARNING_PREFIX)
            ]
            assembled["warnings"] = actionable_warnings
            if assembled["warnings"]:
                assembled["status"] = "done_with_warnings"
            report = self.report_agent.run(assembled)
            save_report(document_id, report, db=db)
            update_document_status(
                db=db,
                document_id=document_id,
                status=str(report.get("status", "done")),
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

