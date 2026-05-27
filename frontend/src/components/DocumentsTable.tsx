import type { DocumentResponse } from "../types/api";
import { formatCount, formatDateTime } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type DocumentsTableProps = {
  documents: DocumentResponse[];
  onRefresh: () => void;
  loading: boolean;
};

export function DocumentsTable({ documents, onRefresh, loading }: DocumentsTableProps) {
  return (
    <section className="card reveal">
      <div className="section-head">
        <h3>Документы</h3>
        <button className="button ghost" onClick={onRefresh} disabled={loading}>
          {loading ? "Обновление..." : "Обновить"}
        </button>
      </div>
      {!documents.length ? (
        <p className="muted">Документов пока нет.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Файл</th>
                <th>Статус</th>
                <th>Текст</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.document_id}>
                  <td>
                    <div className="file-name">{doc.filename}</div>
                    <div className="file-id">{doc.document_id}</div>
                  </td>
                  <td>
                    <StatusBadge value={doc.status} />
                  </td>
                  <td>{formatCount(doc.text_length)}</td>
                  <td>{formatDateTime(doc.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
