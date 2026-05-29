export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(date);
}

export function formatCount(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return new Intl.NumberFormat("ru-RU").format(value);
}
