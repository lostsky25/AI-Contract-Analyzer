import type { ContractReport } from "../types/api";

type OverallRiskBadgeProps = {
  risk: ContractReport["overall_risk"];
};

const LABELS: Record<ContractReport["overall_risk"], string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
  unknown: "Не определен"
};

export function OverallRiskBadge({ risk }: OverallRiskBadgeProps) {
  return <span className={`overall-risk overall-risk-${risk}`}>{LABELS[risk]}</span>;
}
