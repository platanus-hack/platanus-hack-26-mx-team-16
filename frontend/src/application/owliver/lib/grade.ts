/**
 * Grade → color/label helpers. The A–F ramp is the SINGLE source of state color
 * (DESIGN.md "Grade-Is-Data Rule"). Components must read color ONLY from here so
 * it always resolves to the `--grade-*` CSS variable — never a hardcoded hex.
 *
 * The frontend NEVER derives the authoritative grade — the backend (07-scoring)
 * computes it. `gradeFromScore` exists ONLY for display fallbacks (e.g. a
 * per-dimension letter when the API didn't send one) and uses the documented
 * bands.
 */
import type { Grade, Severity } from "../schemas/api";

export const GRADES: readonly Grade[] = ["A", "B", "C", "D", "E", "F"];

/** CSS `var(--grade-*)` reference for a grade. Use as a `color`/`background`. */
export function gradeColorVar(grade: Grade): string {
  return `var(--grade-${grade.toLowerCase()})`;
}

/** The Tailwind text/bg token suffix, e.g. `grade-f`. */
export function gradeToken(grade: Grade): string {
  return `grade-${grade.toLowerCase()}`;
}

/**
 * Display-only banding (07-scoring §5.1). NEVER use this for the authoritative
 * `overallGrade` — only to render a per-dimension letter the API omitted.
 */
export function gradeFromScore(score: number): Grade {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  if (score >= 40) return "E";
  return "F";
}

/** Spanish, human-readable grade caption for a11y/labels. */
export function gradeLabel(grade: Grade): string {
  switch (grade) {
    case "A":
      return "Seguro";
    case "B":
      return "Bueno";
    case "C":
      return "Aceptable";
    case "D":
      return "Deficiente";
    case "E":
      return "Malo";
    case "F":
      return "Reprobado";
  }
}

/** True for the failing grades (used for the red pulse). */
export function isFailingGrade(grade: Grade): boolean {
  return grade === "E" || grade === "F";
}

// ─── Severity ordering + color (severity uses the same A–F ramp tones) ───

export const SEVERITY_ORDER: readonly Severity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

/** Maps a severity onto the grade ramp so chips share the state palette. */
export function severityColorVar(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "var(--grade-f)";
    case "high":
      return "var(--grade-e)";
    case "medium":
      return "var(--grade-d)";
    case "low":
      return "var(--grade-c)";
    case "info":
      return "var(--outline)";
  }
}

export function severityLabel(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "Crítica";
    case "high":
      return "Alta";
    case "medium":
      return "Media";
    case "low":
      return "Baja";
    case "info":
      return "Informativa";
  }
}

/** Stable sort comparator: critical → info (for finding lists). */
export function bySeverityDesc(
  a: { severity: Severity },
  b: { severity: Severity }
): number {
  return SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity);
}
