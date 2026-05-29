from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.document_repository import get_contract_report, save_contract_report

_REPORTS: dict[str, dict] = {}


def save_report(document_id: str, report: dict, db: Session | None = None) -> None:
    _REPORTS[document_id] = dict(report)
    if db is None:
        return
    try:
        save_contract_report(db=db, document_id=document_id, report_payload=report)
    except Exception:
        # Preserve in-memory behavior as a fallback path if DB persistence is unavailable.
        return


def get_report(document_id: str, db: Session | None = None) -> dict | None:
    in_memory = _REPORTS.get(document_id)
    if in_memory is not None:
        return dict(in_memory)

    if db is None:
        return None

    try:
        persisted = get_contract_report(db=db, document_id=document_id)
    except Exception:
        return None
    if persisted is None:
        return None
    _REPORTS[document_id] = dict(persisted)
    return dict(persisted)
