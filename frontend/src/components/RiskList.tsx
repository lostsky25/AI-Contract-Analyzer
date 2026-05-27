import type { Risk } from "../types/api";

type RiskListProps = {
  risks: Risk[];
};

function severityClass(severity: Risk["severity"]): string {
  switch (severity) {
    case "low":
      return "severity severity-low";
    case "medium":
      return "severity severity-medium";
    case "high":
      return "severity severity-high";
    case "critical":
      return "severity severity-critical";
    default:
      return "severity";
  }
}

export function RiskList({ risks }: RiskListProps) {
  if (!risks.length) {
    return <p className="muted">Риски не обнаружены.</p>;
  }

  return (
    <div className="risk-list">
      {risks.map((risk, index) => (
        <article className="risk-card" key={`${risk.type}-${index}`}>
          <div className="risk-card-head">
            <h4>{risk.type}</h4>
            <span className={severityClass(risk.severity)}>{risk.severity}</span>
          </div>
          <p>{risk.description}</p>
          {risk.recommendation ? (
            <p className="recommendation">
              Рекомендация: <strong>{risk.recommendation}</strong>
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}
