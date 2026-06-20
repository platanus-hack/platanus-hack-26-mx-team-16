/**
 * Returns a localized relative time string ("hace 5 minutos" / "5 minutes
 * ago") for recent dates, falling back to an absolute short date for anything
 * older than a week. Returns "-" for null/undefined/invalid input so callers
 * can render directly without extra null-checks.
 *
 * Re-IA 2026-06: localizado vía Intl con el idioma activo de next-intl
 * (leído de `<html lang>`); antes los strings estaban hardcodeados en inglés
 * ("1 hour ago" en UI española).
 */
function activeLocale(): string {
  if (typeof document !== "undefined" && document.documentElement.lang) {
    return document.documentElement.lang;
  }
  return "es";
}

export function formatRelativeDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  const locale = activeLocale();
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });

  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return rtf.format(0, "minute");
  if (diffMins < 60) return rtf.format(-diffMins, "minute");
  if (diffHours < 24) return rtf.format(-diffHours, "hour");
  if (diffDays < 7) return rtf.format(-diffDays, "day");
  return date.toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
