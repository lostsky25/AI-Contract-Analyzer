import type { KeyTerm } from "../types/api";
import { EvidenceQuote } from "./EvidenceQuote";

type KeyTermsListProps = {
  terms: KeyTerm[];
};

export function KeyTermsList({ terms }: KeyTermsListProps) {
  if (!terms.length) {
    return <p className="muted">Ключевые условия пока не выделены.</p>;
  }

  return (
    <div className="key-terms-list">
      {terms.map((term, index) => (
        <article className="term-card" key={`${term.title}-${index}`}>
          <div className="term-head">
            <h4>{term.title}</h4>
            <span className="term-value">{term.value}</span>
          </div>
          <EvidenceQuote quote={term.quote} page={term.page} />
        </article>
      ))}
    </div>
  );
}
