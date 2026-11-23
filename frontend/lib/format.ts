import type { ClassSummary } from "@/types/api";

/** "9" + "А" -> "9А"; already-prefixed labels like "9А" stay unchanged. */
export function className(item: Pick<ClassSummary, "grade" | "label">): string {
  return item.label.startsWith(String(item.grade)) ? item.label : `${item.grade}${item.label}`;
}

export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}

/** ISO date without time ("2026-09-01") — a calendar day, not an instant. */
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Parse a backend date string.
 *
 * Date-only values are calendar days: parse them as UTC and format in UTC,
 * otherwise `new Date("2026-09-01")` (UTC midnight) renders as the previous
 * day for users west of UTC. Datetimes keep the viewer's local timezone.
 */
function parseDate(value: string): { date: Date; dateOnly: boolean } {
  const dateOnly = DATE_ONLY.test(value);
  return { date: new Date(dateOnly ? `${value}T00:00:00Z` : value), dateOnly };
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const { date, dateOnly } = parseDate(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(dateOnly ? { timeZone: "UTC" as const } : {}),
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const { date } = parseDate(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} КБ`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}
