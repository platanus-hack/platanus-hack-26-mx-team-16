import type { PipelinePhase } from "@/src/application/hooks/queries/pipelines";

/**
 * Diff estructural entre dos recetas de pipeline (E6 §2 — publish con diff).
 * Clave de comparación = `phase.id` (estable a través de versiones).
 */

export type PhaseChangeKind = "added" | "removed" | "moved" | "modified";

export interface PhaseChange {
  id: string;
  kind: string;
  change: PhaseChangeKind;
  fromIndex?: number;
  toIndex?: number;
  /** Resumen legible de qué cambió (config) para `modified`. */
  details?: string[];
}

export interface PipelineDiff {
  phases: PhaseChange[];
  /** True si no hubo ningún cambio estructural. */
  empty: boolean;
}

function stable(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") {
    // Objeto/arreglo vacío == sin valor (un policy `{}` cargado de un `null`
    // no debe leerse como un cambio).
    if (Object.keys(value).length === 0) return "—";
    return JSON.stringify(sortKeys(value));
  }
  return String(value);
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as Record<string, unknown>)
        .sort()
        .map((k) => [k, sortKeys((value as Record<string, unknown>)[k])])
    );
  }
  return value;
}

function diffConfig(
  before: Record<string, unknown>,
  after: Record<string, unknown>
): string[] {
  const keys = new Set([
    ...Object.keys(before ?? {}),
    ...Object.keys(after ?? {}),
  ]);
  const out: string[] = [];
  for (const key of keys) {
    const b = stable(before?.[key]);
    const a = stable(after?.[key]);
    if (b !== a) out.push(`${key}: ${b} → ${a}`);
  }
  return out;
}

export function diffPhases(
  before: PipelinePhase[],
  after: PipelinePhase[]
): PhaseChange[] {
  const beforeIndex = new Map(before.map((p, i) => [p.id, { phase: p, i }]));
  const afterIndex = new Map(after.map((p, i) => [p.id, { phase: p, i }]));
  const changes: PhaseChange[] = [];

  for (const p of before) {
    if (!afterIndex.has(p.id)) {
      changes.push({
        id: p.id,
        kind: p.kind,
        change: "removed",
        fromIndex: beforeIndex.get(p.id)?.i,
      });
    }
  }

  for (const [i, p] of after.entries()) {
    const prev = beforeIndex.get(p.id);
    if (!prev) {
      changes.push({ id: p.id, kind: p.kind, change: "added", toIndex: i });
      continue;
    }
    const details: string[] = [];
    const configDiff = diffConfig(prev.phase.config, p.config);
    if (configDiff.length) details.push(...configDiff);
    if (details.length) {
      changes.push({ id: p.id, kind: p.kind, change: "modified", details });
    } else if (prev.i !== i) {
      changes.push({
        id: p.id,
        kind: p.kind,
        change: "moved",
        fromIndex: prev.i,
        toIndex: i,
      });
    }
  }

  return changes;
}

export function computePipelineDiff(
  before: { phases: PipelinePhase[] },
  after: { phases: PipelinePhase[] }
): PipelineDiff {
  // Las policies van plegadas en config de fase (completitud → await_documents.config,
  // activación → extraction_gate.config.activation, D-A): sus cambios aparecen como diff
  // de config de esas fases vía diffPhases. Ya no hay diff de policy a nivel-versión.
  const phases = diffPhases(before.phases, after.phases);
  return { phases, empty: phases.length === 0 };
}
