type StatusBadgeProps = {
  value: string;
};

function normalizeStatus(status: string): string {
  return status.trim().toLowerCase();
}

function mapClass(status: string): string {
  switch (normalizeStatus(status)) {
    case "uploaded":
      return "status status-uploaded";
    case "processed":
    case "extracted":
    case "indexed":
      return "status status-processed";
    case "analyzed":
      return "status status-analyzed";
    case "empty_text":
      return "status status-warning";
    default:
      return "status status-default";
  }
}

export function StatusBadge({ value }: StatusBadgeProps) {
  return <span className={mapClass(value)}>{value}</span>;
}
