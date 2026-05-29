from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.db_models import Document, User
from app.database import Base
from app.services.report_store import get_report, save_report


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_local()


def test_report_store_persists_and_reads_from_db() -> None:
    session = _build_session()
    try:
        user = User(
            id="user-1",
            username="u1",
            email="u1@example.com",
            hashed_password="hash",
            is_active=True,
        )
        document = Document(
            id="doc-1",
            user_id="user-1",
            filename="demo.docx",
            file_path="/tmp/demo.docx",
            status="uploaded",
        )
        session.add(user)
        session.add(document)
        session.commit()

        report = {
            "document_id": "doc-1",
            "status": "done_with_warnings",
            "summary": "Demo summary",
            "overall_risk": "medium",
            "risks": [],
            "key_terms": [],
            "legal_sources": [],
            "warnings": ["Legal web search provider is unavailable."],
            "disclaimer": "Demo disclaimer",
            "used_ocr": False,
            "chunks_count": 1,
        }
        save_report("doc-1", report, db=session)

        # Simulate API restart by clearing in-memory cache.
        import app.services.report_store as report_store_module

        report_store_module._REPORTS.clear()

        loaded = get_report("doc-1", db=session)
        assert loaded is not None
        assert loaded["document_id"] == "doc-1"
        assert loaded["status"] == "done_with_warnings"
        assert loaded["summary"] == "Demo summary"
    finally:
        session.close()
