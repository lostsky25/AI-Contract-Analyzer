import type { Risk } from "../types/api";
import { RiskCard } from "./RiskCard";

type RiskListProps = {
  risks: Risk[];
};

export function RiskList({ risks }: RiskListProps) {
  if (!risks.length) {
    return <p className="muted">Риски не обнаружены.</p>;
  }

  return (
    <div className="risk-list">
      {risks.map((risk, index) => (
        <RiskCard risk={risk} key={`${risk.title}-${index}`} />
      ))}
    </div>
  );
}
