from typing import Any

DISCLAIMER = "Система выполняет предварительный анализ и не заменяет профессионального юриста."


def _normalize_risk(risk: dict[str, Any]) -> dict[str, Any]:
    explanation = str(
        risk.get("explanation") or risk.get("description") or ""
    ).strip()
    quote = str(risk.get("quote") or explanation).strip()
    return {
        "title": str(risk.get("title") or risk.get("type") or "Risk").strip() or "Risk",
        "severity": str(risk.get("severity", "unknown")).lower(),
        "explanation": explanation,
        "quote": quote or "Цитата не указана.",
        "page": risk.get("page"),
    }


def _normalize_key_term(term: dict[str, Any]) -> dict[str, Any]:
    value = str(term.get("value") or "").strip()
    quote = str(term.get("quote") or value).strip()
    return {
        "title": str(term.get("title") or "Key term").strip() or "Key term",
        "value": value or "Не указано",
        "quote": quote or "Цитата не указана.",
        "page": term.get("page"),
    }


class ReportAgent:
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = dict(payload)
        report["status"] = str(report.get("status", "done"))
        report["summary"] = str(report.get("summary", "")).strip()
        report["overall_risk"] = str(report.get("overall_risk", "unknown")).lower()
        report["risks"] = [_normalize_risk(risk) for risk in list(report.get("risks", []))]
        report["key_terms"] = [
            _normalize_key_term(term) for term in list(report.get("key_terms", []))
        ]
        report["legal_sources"] = list(report.get("legal_sources", []))
        report["warnings"] = list(report.get("warnings", []))
        if report["status"] not in {"failed", "processing"}:
            if not report["legal_sources"] and report["warnings"]:
                report["status"] = "done_with_warnings"
        report["disclaimer"] = DISCLAIMER
        return report
