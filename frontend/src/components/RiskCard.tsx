import type { Risk } from "../types/api";
import { formatSeverityLabel } from "../utils/labels";
import { EvidenceQuote } from "./EvidenceQuote";

type RiskCardProps = {
  risk: Risk;
};

function severityClass(severity: Risk["severity"]): string {
  return `severity severity-${severity}`;
}

function RiskIndicatorIcon({ severity }: { severity: Risk["severity"] }) {
  if (severity === "low") {
    return (
      <svg viewBox="0 0 24 24" className="risk-indicator-icon" role="presentation">
        <path d="M12 2 19 5v6.1c0 5.1-3.2 9.5-7 10.9-3.8-1.4-7-5.8-7-10.9V5L12 2Z" />
        <path d="m8.6 12.2 2.3 2.4 4.5-4.7" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="risk-indicator-icon" role="presentation">
      <path d="M12 2 19 5v6.1c0 5.1-3.2 9.5-7 10.9-3.8-1.4-7-5.8-7-10.9V5L12 2Z" />
      <path d="M12 7.1v6.2M12 16.8h.01" />
    </svg>
  );
}

export function RiskCard({ risk }: RiskCardProps) {
  return (
    <article className="risk-card">
      <div className="risk-layout">
        <div className={`risk-indicator risk-indicator-${risk.severity}`} aria-hidden>
          <RiskIndicatorIcon severity={risk.severity} />
        </div>
        <div className="risk-content">
          <div className="risk-card-head">
            <h4>{risk.title}</h4>
            <span className={severityClass(risk.severity)}>{formatSeverityLabel(risk.severity)}</span>
          </div>
          <p className="risk-explanation">{risk.explanation}</p>
        </div>
        <span className="risk-chevron" aria-hidden>
          ›
        </span>
      </div>
      <div className="risk-evidence">
        <EvidenceQuote quote={risk.quote} page={risk.page} sourceLabel="Цитата из договора" />
      </div>
    </article>
  );
}
