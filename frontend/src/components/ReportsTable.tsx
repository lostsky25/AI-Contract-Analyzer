import type { ContractReport, DocumentResponse } from "../types/api";
import { formatDateTime } from "../utils/format";
import { formatOverallRiskLabel } from "../utils/labels";
import { StatusBadge } from "./StatusBadge";

type ReportsTableProps = {
  documents: DocumentResponse[];
  loading: boolean;
  selectedDocumentId?: string | null;
  openingReportDocumentId?: string | null;
  currentReport: ContractReport | null;
  reportCache: Record<string, ContractReport>;
  onOpenReport: (document: DocumentResponse) => void;
  onRefresh: () => void;
};

function isReportCandidate(status: string): boolean {
  return ["done", "done_with_warnings", "analyzed"].includes(status.trim().toLowerCase());
}

export function ReportsTable({
  documents,
  loading,
  selectedDocumentId,
  openingReportDocumentId,
  currentReport,
  reportCache,
  onOpenReport,
  onRefresh
}: ReportsTableProps) {
  const reportDocs = documents.filter((doc) => isReportCandidate(doc.status));

  return (
    <section className="card reveal">
      <div className="section-head">
        <h3>Отчеты</h3>
        <button className="button ghost" onClick={onRefresh} disabled={loading} type="button">
          {loading ? "Обновление..." : "Обновить"}
        </button>
      </div>

      {!reportDocs.length ? (
        <p className="muted">Отчеты появятся после завершения анализа документов.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Документ</th>
                <th>Статус</th>
                <th>Общий риск</th>
                <th>Риски</th>
                <th>Ключевые условия</th>
                <th>Дата</th>
                <th>Действие</th>
              </tr>
            </thead>
            <tbody>
              {reportDocs.map((doc) => {
                const selected = doc.document_id === selectedDocumentId;
                const opening = openingReportDocumentId === doc.document_id;
                const resolvedReport = (selected ? currentReport : null) ?? reportCache[doc.document_id] ?? null;
                const hasLoadedReport = Boolean(resolvedReport);
                return (
                  <tr key={doc.document_id} className={selected ? "table-row-selected" : undefined}>
                    <td>{doc.filename}</td>
                    <td>
                      <StatusBadge value={doc.status} />
                    </td>
                    <td>{hasLoadedReport ? formatOverallRiskLabel(resolvedReport.overall_risk) : "—"}</td>
                    <td>{hasLoadedReport ? resolvedReport.risks.length : "—"}</td>
                    <td>{hasLoadedReport ? resolvedReport.key_terms.length : "—"}</td>
                    <td>{formatDateTime(doc.created_at)}</td>
                    <td>
                      <button
                        className="button ghost"
                        type="button"
                        onClick={() => onOpenReport(doc)}
                        disabled={opening}
                      >
                        {opening ? "Загружаем отчет..." : "Открыть"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
