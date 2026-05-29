_REPORTS: dict[str, dict] = {}


def save_report(document_id: str, report: dict) -> None:
    _REPORTS[document_id] = report


def get_report(document_id: str) -> dict | None:
    return _REPORTS.get(document_id)
