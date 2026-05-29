type EvidenceQuoteProps = {
  quote?: string;
  page?: number | null;
};

export function EvidenceQuote({ quote, page }: EvidenceQuoteProps) {
  if (!quote && !page) {
    return <p className="muted">Цитата и страница не указаны.</p>;
  }

  return (
    <div className="evidence-quote">
      {quote ? <blockquote>{quote}</blockquote> : null}
      {page ? <span className="evidence-page">стр. {page}</span> : null}
    </div>
  );
}
