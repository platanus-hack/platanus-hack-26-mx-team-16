/**
 * Format a confidence in the [0..1] range as a percentage string, keeping
 * up to two decimals and dropping trailing zeros.
 *
 * `formatConfidencePct(0.9998)` → `"99.98"`, `formatConfidencePct(0.9)` → `"90"`.
 */
export function formatConfidencePct(c: number): string {
  return (Math.round(c * 100 * 100) / 100).toString();
}

export type ConfidenceBand = "high" | "medium" | "low";

/**
 * Bucket a [0..1] confidence into the trust bands the UI colours by:
 * success (high), warning (medium), destructive (low). Shared so the PDF
 * overlay and the field list classify a value identically.
 */
export function confidenceBand(c: number): ConfidenceBand {
  if (c >= 0.9) return "high";
  if (c >= 0.7) return "medium";
  return "low";
}
