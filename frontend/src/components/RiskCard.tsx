import type { Risk } from "../types/api";
import { EvidenceQuote } from "./EvidenceQuote";

type RiskCardProps = {
  risk: Risk;
};

function severityClass(severity: Risk["severity"]): string {
  return `severity severity-${severity}`;
}

export function RiskCard({ risk }: RiskCardProps) {
  return (
    <article className="risk-card">
      <div className="risk-card-head">
        <h4>{risk.title}</h4>
        <span className={severityClass(risk.severity)}>{risk.severity}</span>
      </div>
      <p>{risk.explanation}</p>
      <EvidenceQuote quote={risk.quote} page={risk.page} />
    </article>
  );
}
