import type { ContractReport } from "../types/api";
import { formatOverallRiskLabel } from "../utils/labels";

type OverallRiskBadgeProps = {
  risk: ContractReport["overall_risk"];
};

export function OverallRiskBadge({ risk }: OverallRiskBadgeProps) {
  return <span className={`overall-risk overall-risk-${risk}`}>{formatOverallRiskLabel(risk)}</span>;
}
