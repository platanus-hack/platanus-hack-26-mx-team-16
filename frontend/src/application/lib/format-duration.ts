/**
 * Formats a millisecond duration as a compact human-readable string
 * (e.g. "45s", "12m 30s", "2h 5m"). Returns null for null/undefined/negative
 * input.
 */
export function formatDuration(ms: number | null | undefined): string | null {
  if (ms == null || ms < 0) return null;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rs = seconds % 60;
  if (minutes < 60) return rs > 0 ? `${minutes}m ${rs}s` : `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rm = minutes % 60;
  return rm > 0 ? `${hours}h ${rm}m` : `${hours}h`;
}
