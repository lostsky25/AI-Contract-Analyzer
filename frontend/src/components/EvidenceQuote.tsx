import { useMemo, useState } from "react";

type EvidenceQuoteProps = {
  quote?: string;
  page?: number | null;
  sourceLabel?: string;
};

const COLLAPSE_AT = 260;

export function EvidenceQuote({ quote, page, sourceLabel }: EvidenceQuoteProps) {
  const normalized = String(quote ?? "").trim();
  const [expanded, setExpanded] = useState(false);

  const isLong = normalized.length > COLLAPSE_AT;
  const preview = useMemo(() => normalized.slice(0, COLLAPSE_AT).trimEnd(), [normalized]);
  const visibleText = isLong && !expanded ? `${preview}...` : normalized;

  if (!normalized && typeof page !== "number") {
    return <p className="muted">Цитата не указана.</p>;
  }

  return (
    <div className="evidence-quote">
      <div className="evidence-quote-head">
        {sourceLabel ? <span className="status status-default">{sourceLabel}</span> : null}
        {typeof page === "number" ? <span className="page-pill">стр. {page}</span> : null}
      </div>
      {normalized ? <blockquote>{visibleText}</blockquote> : null}
      {isLong ? (
        <button
          type="button"
          className="button text evidence-toggle"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Свернуть" : "Показать полностью"}
        </button>
      ) : null}
    </div>
  );
}
