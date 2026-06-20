export const MONTHS_ES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
] as const;

const MONTHS_SHORT_ES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
] as const;

const MONTHS_SHORT_EN = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

export const DAY_HEADERS_ES = [
  "lu",
  "ma",
  "mi",
  "ju",
  "vi",
  "sá",
  "do",
] as const;

export function parseLocalDate(s: string): Date | null {
  if (!s) return null;
  const [y, m, d] = s.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

export function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function formatShortDate(iso: string, locale = "es"): string {
  const d = parseLocalDate(iso);
  if (!d) return "";
  const months = locale === "es" ? MONTHS_SHORT_ES : MONTHS_SHORT_EN;
  return `${d.getDate()}/${months[d.getMonth()]}/${d.getFullYear()}`;
}

export function formatDateRangeLabel(
  from: string,
  to: string,
  locale = "es",
  placeholder = "Rango de fechas",
): string {
  if (from && to) return `${formatShortDate(from, locale)} – ${formatShortDate(to, locale)}`;
  if (from) return `desde ${formatShortDate(from, locale)}`;
  if (to) return `hasta ${formatShortDate(to, locale)}`;
  return placeholder;
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

export function firstDayOffset(year: number, month: number): number {
  return (new Date(year, month, 1).getDay() + 6) % 7;
}

export function shiftMonth(
  year: number,
  month: number,
  delta: number,
): [number, number] {
  const d = new Date(year, month + delta, 1);
  return [d.getFullYear(), d.getMonth()];
}
