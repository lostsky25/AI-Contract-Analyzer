import { formatStatusLabel } from "../utils/labels";

type StatusBadgeProps = {
  value: string;
};

function normalizeStatus(status: string): string {
  return status.trim().toLowerCase();
}

export function statusLabel(status: string): string {
  return formatStatusLabel(status);
}

function mapClass(status: string): string {
  switch (normalizeStatus(status)) {
    case "uploaded":
      return "status status-uploaded";
    case "processing":
    case "analyzing":
      return "status status-uploaded";
    case "processed":
    case "extracted":
    case "indexed":
      return "status status-processed";
    case "analyzed":
    case "done":
      return "status status-analyzed";
    case "done_with_warnings":
    case "empty_text":
      return "status status-warning";
    case "failed":
    case "failed_processing":
      return "status status-failed";
    default:
      return "status status-default";
  }
}

export function StatusBadge({ value }: StatusBadgeProps) {
  return <span className={mapClass(value)}>{statusLabel(value)}</span>;
}
