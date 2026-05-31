import { useMemo } from "react";

import type { LegalSource } from "../types/api";
import {
  getLegalSourceTrustLabel,
  getLegalSourceTrustTone,
  getLegalSourceTypeLabel,
  getRelevanceLabel
} from "../utils/labels";

type LegalSourcesPanelProps = {
  legalSources: LegalSource[];
  legalWarnings?: string[];
};

export function LegalSourcesPanel({ legalSources, legalWarnings = [] }: LegalSourcesPanelProps) {
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

  const hasModelReportedSources = useMemo(
    () => uniqueSources.some((source) => source.trust_tier === "model_reported"),
    [uniqueSources]
  );

  const uniqueWarnings = useMemo(() => {
    const seen = new Set<string>();
    return legalWarnings.filter((warning) => {
      const normalized = warning.trim();
      if (!normalized || seen.has(normalized)) {
        return false;
      }
      seen.add(normalized);
      return true;
    });
  }, [legalWarnings]);

  if (!uniqueSources.length) {
    return (
      <article className="legal-empty-card">
        <h4>Правовые источники не найдены</h4>
        <p className="muted">
          Правовые источники не найдены или web-проверка была недоступна. Основной анализ рисков и условий выполнен
          по тексту договора.
        </p>
        {uniqueWarnings.length ? (
          <div className="legal-notice-block" aria-live="polite">
            <p className="legal-notice-title">Пояснение</p>
            <ul className="legal-notice-list">
              {uniqueWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </article>
    );
  }

  return (
    <div className="legal-sources-wrap">
      {hasModelReportedSources ? (
        <div className="legal-notice-block" aria-live="polite">
          <p className="legal-notice-title">Проверка источников</p>
          <p className="muted legal-notice-text">
            Эти источники получены из структурированного ответа модели и требуют ручной проверки.
          </p>
        </div>
      ) : null}

      {uniqueWarnings.length ? (
        <div className="legal-notice-block" aria-live="polite">
          <p className="legal-notice-title">Пояснение</p>
          <ul className="legal-notice-list">
            {uniqueWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="legal-sources-list">
        {uniqueSources.map((source, index) => {
          const trustTone = getLegalSourceTrustTone(source.trust_tier);
          return (
            <article className="legal-source-card" key={`${source.url}-${index}`}>
              <div className="legal-source-head">
                <h4>{source.title}</h4>
                <div className="legal-source-meta">
                  <span className="source-chip">{getLegalSourceTypeLabel(source.source_type)}</span>
                  <span className={`severity severity-${source.relevance}`}>{getRelevanceLabel(source.relevance)}</span>
                  <span className={`trust-chip trust-${trustTone}`}>{getLegalSourceTrustLabel(source.trust_tier)}</span>
                </div>
              </div>
              <p>{source.snippet}</p>
              {source.reason ? <p className="legal-source-reason">{source.reason}</p> : null}
              <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                Открыть источник
              </a>
            </article>
          );
        })}
      </div>
    </div>
  );
}
