from sqlalchemy.orm import Session

from app.models.db_models import AnalysisReport, Document


def create_document(
    db: Session,
    document_id: str,
    user_id: str,
    filename: str,
    file_path: str,
    status: str,
) -> Document:
    document = Document(
        id=document_id,
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        status=status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, document_id: str, user_id: str | None = None) -> Document | None:
    query = db.query(Document).filter(Document.id == document_id)
    if user_id is not None:
        query = query.filter(Document.user_id == user_id)
    return query.first()


def list_documents(db: Session, user_id: str | None = None) -> list[Document]:
    query = db.query(Document)
    if user_id is not None:
        query = query.filter(Document.user_id == user_id)
    return query.order_by(Document.created_at.desc()).all()


def update_document_status(
    db: Session,
    document_id: str,
    status: str,
    text_length: int | None = None,
    user_id: str | None = None,
) -> Document | None:
    document = get_document(db, document_id, user_id=user_id)
    if document is None:
        return None

    document.status = status
    if text_length is not None:
        document.text_length = text_length

    db.commit()
    db.refresh(document)
    return document


def create_analysis_report(
    db: Session,
    document_id: str,
    summary: str,
    risks: list[dict],
) -> AnalysisReport:
    report = AnalysisReport(
        document_id=document_id,
        summary=summary,
        risks=risks,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
