import type { LegalSource } from "../types/api";

type LegalSourcesPanelProps = {
  legalSources: LegalSource[];
};

function sourceLabel(sourceType: LegalSource["source_type"]): string {
  switch (sourceType) {
    case "consultant_plus":
      return "Consultant Plus";
    case "garant":
      return "Garant";
    case "pravo_gov":
      return "pravo.gov.ru";
    default:
      return "Публичный источник";
  }
}

export function LegalSourcesPanel({ legalSources }: LegalSourcesPanelProps) {
  if (!legalSources.length) {
    return (
      <p className="muted legal-empty">
        Правовые источники не найдены или web-проверка недоступна. Анализ выполнен по тексту договора.
      </p>
    );
  }

  return (
    <div className="legal-sources-list">
      {legalSources.map((source, index) => (
        <article className="legal-source-card" key={`${source.title}-${index}`}>
          <div className="legal-source-head">
            <h4>{source.title}</h4>
            <div className="legal-source-meta">
              <span className="status status-default">{sourceLabel(source.source_type)}</span>
              <span className="status status-default">{source.source_type}</span>
              <span className={`severity severity-${source.relevance}`}>{source.relevance}</span>
            </div>
          </div>
          <p>{source.snippet}</p>
          <a href={source.url} target="_blank" rel="noreferrer" className="source-link">
            {source.url}
          </a>
        </article>
      ))}
    </div>
  );
}
