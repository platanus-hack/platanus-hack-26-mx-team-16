const MONTHS_ES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

/**
 * Formatea una fecha ISO al patrón "dd/Mes/yyyy HH:mm" en español
 * (p.ej. "01/Abril/2026 09:30"). Devuelve null cuando el input es
 * null/undefined/inválido para que el caller renderice su placeholder.
 */
export function formatDateTime(
  value: string | null | undefined
): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const day = String(d.getDate()).padStart(2, "0");
  const month = MONTHS_ES[d.getMonth()];
  const year = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${day}/${month}/${year} ${hh}:${mm}`;
}
