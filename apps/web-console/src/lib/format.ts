export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0%";
  }
  return `${Math.round((value / total) * 100)}%`;
}

export function formatDateTime(value?: string | null): string {
  if (!value) {
    return "never";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function toJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
