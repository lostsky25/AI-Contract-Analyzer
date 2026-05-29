import type { DocumentResponse } from "../types/api";
import { formatCount, formatDateTime } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type DocumentsTableProps = {
  documents: DocumentResponse[];
  onRefresh: () => void;
  loading: boolean;
  searchQuery?: string;
  onSelect?: (document: DocumentResponse) => void;
  selectedDocumentId?: string | null;
};

export function DocumentsTable({
  documents,
  onRefresh,
  loading,
  searchQuery,
  onSelect,
  selectedDocumentId
}: DocumentsTableProps) {
  return (
    <section className="card reveal">
      <div className="section-head">
        <h3>Документы</h3>
        <button className="button ghost" onClick={onRefresh} disabled={loading} type="button">
          {loading ? "Обновление..." : "Обновить"}
        </button>
      </div>
      {!documents.length ? (
        <p className="muted">
          {searchQuery?.trim() ? "Документы по запросу не найдены." : "Документов пока нет."}
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Файл</th>
                <th>Статус</th>
                <th>Символов</th>
                <th>Создан</th>
                {onSelect ? <th>Действие</th> : null}
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const isSelected = doc.document_id === selectedDocumentId;
                return (
                  <tr key={doc.document_id} className={isSelected ? "table-row-selected" : undefined}>
                    <td>
                      <div className="file-name">{doc.filename}</div>
                      <div className="file-subline">{formatDateTime(doc.created_at)}</div>
                    </td>
                    <td>
                      <StatusBadge value={doc.status} />
                    </td>
                    <td>{formatCount(doc.text_length)}</td>
                    <td>{formatDateTime(doc.created_at)}</td>
                    {onSelect ? (
                      <td>
                        <button className="button ghost" type="button" onClick={() => onSelect(doc)}>
                          {isSelected ? "Открыто" : "Открыть"}
                        </button>
                      </td>
                    ) : null}
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
