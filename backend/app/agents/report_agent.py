from typing import Any

DISCLAIMER = "Система выполняет предварительный анализ и не заменяет профессионального юриста."


class ReportAgent:
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = dict(payload)
        report["status"] = str(report.get("status", "done"))
        report["summary"] = str(report.get("summary", "")).strip()
        report["overall_risk"] = str(report.get("overall_risk", "unknown")).lower()
        report["risks"] = list(report.get("risks", []))
        report["key_terms"] = list(report.get("key_terms", []))
        report["legal_sources"] = list(report.get("legal_sources", []))
        report["warnings"] = list(report.get("warnings", []))
        if report["status"] not in {"failed", "processing"}:
            if not report["legal_sources"] and report["warnings"]:
                report["status"] = "done_with_warnings"
        report["disclaimer"] = DISCLAIMER
        return report
