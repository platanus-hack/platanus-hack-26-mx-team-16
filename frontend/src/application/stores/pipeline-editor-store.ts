import { arrayMove } from "@dnd-kit/sortable";
import { create } from "zustand";

import type {
  PhaseCatalogEntry,
  PipelinePhase,
  PipelineVersion,
} from "@/src/application/hooks/queries/pipelines";

/**
 * Draft client-side del editor de pipelines (E6 §2). El backend es append-only
 * inmutable: no hay PipelineStatus.DRAFT en uso, así que el borrador vive aquí
 * y el publish (POST .../versions) avanza la versión activa al instante — por eso
 * el modal de diff pre-publish es obligatorio.
 *
 * Las policies ya NO son version-level: completitud → await_documents.config,
 * activación → extraction_gate.config.activation (D-A). Todo vive en phases.
 */

export function makePhaseId(kind: string, existing: PipelinePhase[]): string {
  const base = kind.replace(/[^a-z0-9_]/gi, "_");
  let candidate = base;
  let n = 1;
  const taken = new Set(existing.map((p) => p.id));
  while (taken.has(candidate)) {
    n += 1;
    candidate = `${base}_${n}`;
  }
  return candidate;
}

interface PipelineEditorState {
  /** UUID del pipeline en edición (null = sin cargar). */
  pipelineId: string | null;
  /** Versión base desde la que se editó (para el diff pre-publish). */
  baseVersion: number | null;
  /**
   * Contador que sube en cada `load`/`reset`. El editor visual (spine) es
   * uncontrolled: el host lo re-monta con `key` cuando esto cambia, para
   * re-sembrar su estado interno tras cargar/descartar una versión.
   */
  loadNonce: number;
  phases: PipelinePhase[];
  outputSchema: Record<string, unknown> | null;
  dirty: boolean;

  load: (pipelineId: string, version: PipelineVersion) => void;
  reset: () => void;

  // Phase CRUD
  addPhase: (entry: PhaseCatalogEntry) => void;
  removePhase: (id: string) => void;
  /** Quita varias fases de una vez (quitar una etapa/capacidad completa). */
  removePhases: (ids: string[]) => void;
  /**
   * Reemplaza las fases de una sola tacada (toggle de capacidad: el helper puro
   * calcula el draft nuevo —orden canónico— y lo aplica aquí). Marca dirty.
   */
  setDraft: (partial: { phases?: PipelinePhase[] }) => void;
  movePhase: (activeId: string, overId: string) => void;
  updatePhaseConfig: (id: string, config: Record<string, unknown>) => void;
}

export const usePipelineEditorStore = create<PipelineEditorState>((set) => ({
  pipelineId: null,
  baseVersion: null,
  loadNonce: 0,
  phases: [],
  outputSchema: null,
  dirty: false,

  load: (pipelineId, version) =>
    set((s) => ({
      pipelineId,
      baseVersion: version.version,
      loadNonce: s.loadNonce + 1,
      phases: version.phases.map((p) => ({
        id: p.id,
        kind: p.kind,
        config: { ...(p.config ?? {}) },
      })),
      outputSchema: version.outputSchema ?? null,
      dirty: false,
    })),

  reset: () =>
    set((s) => ({
      pipelineId: null,
      baseVersion: null,
      loadNonce: s.loadNonce + 1,
      phases: [],
      outputSchema: null,
      dirty: false,
    })),

  addPhase: (entry) =>
    set((s) => {
      // Defaults del configSchema (solo los campos con default declarado).
      const config: Record<string, unknown> = {};
      for (const [key, field] of Object.entries(entry.configSchema)) {
        if (field.default !== undefined) config[key] = field.default;
      }
      const phase: PipelinePhase = {
        id: makePhaseId(entry.kind, s.phases),
        kind: entry.kind,
        config,
      };
      return { phases: [...s.phases, phase], dirty: true };
    }),

  removePhase: (id) =>
    set((s) => ({ phases: s.phases.filter((p) => p.id !== id), dirty: true })),

  removePhases: (ids) =>
    set((s) => {
      if (!ids.length) return s;
      const drop = new Set(ids);
      return { phases: s.phases.filter((p) => !drop.has(p.id)), dirty: true };
    }),

  setDraft: (partial) =>
    set((s) => ({ phases: partial.phases ?? s.phases, dirty: true })),

  movePhase: (activeId, overId) =>
    set((s) => {
      const from = s.phases.findIndex((p) => p.id === activeId);
      const to = s.phases.findIndex((p) => p.id === overId);
      if (from === -1 || to === -1 || from === to) return s;
      return { phases: arrayMove(s.phases, from, to), dirty: true };
    }),

  updatePhaseConfig: (id, config) =>
    set((s) => ({
      phases: s.phases.map((p) => (p.id === id ? { ...p, config } : p)),
      dirty: true,
    })),
}));
