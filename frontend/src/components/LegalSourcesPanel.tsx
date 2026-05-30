import { useMemo } from "react";

import type { LegalSource } from "../types/api";
import { formatRelevanceLabel, formatSourceTypeLabel } from "../utils/labels";

type LegalSourcesPanelProps = {
  legalSources: LegalSource[];
};

export function LegalSourcesPanel({ legalSources }: LegalSourcesPanelProps) {
  const uniqueSources = useMemo(() => {
    const seen = new Set<string>();
    return legalSources.filter((source) => {
      const key = `${source.url.trim().toLowerCase()}::${source.title.trim().toLowerCase()}`;
      if (!key || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [legalSources]);

  if (!uniqueSources.length) {
    return <p className="muted legal-empty">Правовые источники не найдены или web-проверка недоступна.</p>;
  }

  return (
    <div className="legal-sources-list">
      {uniqueSources.map((source, index) => (
        <article className="legal-source-card" key={`${source.url}-${index}`}>
          <div className="legal-source-head">
            <h4>{source.title}</h4>
            <div className="legal-source-meta">
              <span className="source-chip">{formatSourceTypeLabel(source.source_type)}</span>
              <span className={`severity severity-${source.relevance}`}>{formatRelevanceLabel(source.relevance)}</span>
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
