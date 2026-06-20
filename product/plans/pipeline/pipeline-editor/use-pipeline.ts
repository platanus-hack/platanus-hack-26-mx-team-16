"use client";
// use-pipeline.ts — state hook. Manages spine order, collapse, optional toggles,
// config overrides and selection. Uncontrolled by default; emits `onChange`.
import * as React from "react";
import type { Stage, PipelineState, Selection } from "./types";
import { validatePipeline } from "./layout";

export interface UsePipelineOptions {
  stages: Stage[];
  initialState: PipelineState;
  /** Stage ids insertable via the "+" menu. Defaults to all removable stages. */
  addable?: string[];
  onChange?: (state: PipelineState) => void;
  onSelect?: (sel: Selection) => void;
}

export function usePipeline(opts: UsePipelineOptions) {
  const { stages, initialState, onChange, onSelect } = opts;
  const byId = React.useMemo(
    () => Object.fromEntries(stages.map((s) => [s.id, s])) as Record<string, Stage>,
    [stages],
  );
  const addable = React.useMemo(
    () => opts.addable ?? stages.filter((s) => s.removable).map((s) => s.id),
    [opts.addable, stages],
  );

  const [state, setState] = React.useState<PipelineState>(initialState);
  const [sel, setSelInternal] = React.useState<Selection>(null);
  const [flash, setFlash] = React.useState<string | null>(null);
  const flashTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const emit = React.useCallback(
    (next: PipelineState) => { onChange?.(next); return next; },
    [onChange],
  );
  const update = React.useCallback(
    (fn: (s: PipelineState) => PipelineState) => setState((s) => emit(fn(s))),
    [emit],
  );

  const setSel = React.useCallback(
    (s: Selection) => { setSelInternal(s); onSelect?.(s); },
    [onSelect],
  );

  const doFlash = React.useCallback((msg: string) => {
    setFlash(msg);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setFlash(null), 2600);
  }, []);
  React.useEffect(() => () => { if (flashTimer.current) clearTimeout(flashTimer.current); }, []);

  const orderedStages = React.useMemo(
    () => state.order.map((id) => byId[id]).filter(Boolean),
    [state.order, byId],
  );

  // ── structural actions ────────────────────────────────────────────────────
  const toggleCollapse = React.useCallback((id: string) => {
    update((s) => ({ ...s, collapsed: { ...s.collapsed, [id]: !s.collapsed[id] } }));
  }, [update]);

  const toggleOptional = React.useCallback((kind: string) => {
    update((s) => ({ ...s, optional: { ...s.optional, [kind]: s.optional[kind] === false } }));
  }, [update]);

  const setConfig = React.useCallback(
    (stageId: string, kind: string, key: string, value: string | number) => {
      update((s) => ({
        ...s,
        config: {
          ...s.config,
          [stageId]: {
            ...(s.config[stageId] ?? {}),
            [kind]: { ...((s.config[stageId] ?? {})[kind] ?? {}), [key]: value },
          },
        },
      }));
    },
    [update],
  );
  const getConfig = React.useCallback(
    (stageId: string, kind: string, key: string): string | number | undefined =>
      state.config[stageId]?.[kind]?.[key],
    [state.config],
  );

  const reorder = React.useCallback((id: string, targetIdx: number) => {
    setState((s) => {
      const cur = s.order.indexOf(id);
      if (cur < 0) return s;
      let target = targetIdx;
      if (target > cur) target--;
      if (target === cur) return s;
      const next = s.order.slice();
      next.splice(cur, 1);
      next.splice(target, 0, id);
      const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
      if (v.some((m) => m.level === "error")) {
        doFlash("No se puede: rompería la frontera de scope (documento → caso).");
        return s;
      }
      return emit({ ...s, order: next });
    });
  }, [byId, doFlash, emit]);

  const removeStage = React.useCallback((id: string) => {
    update((s) => ({ ...s, order: s.order.filter((x) => x !== id) }));
    setSelInternal((cur) => (cur && cur.stageId === id ? null : cur));
  }, [update]);

  const insertStage = React.useCallback((id: string, atIdx: number) => {
    setState((s) => {
      if (s.order.includes(id)) return s;
      const next = s.order.slice();
      next.splice(atIdx, 0, id);
      const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
      if (v.some((m) => m.level === "error")) {
        doFlash("Esa posición rompería la frontera de scope.");
        return s;
      }
      return emit({ ...s, order: next });
    });
  }, [byId, doFlash, emit]);

  /** Toggle a toggleable group (e.g. quality control) in/out of the spine. */
  const toggleStage = React.useCallback((id: string, afterId?: string) => {
    setState((s) => {
      if (s.order.includes(id)) {
        setSelInternal((cur) => (cur && cur.stageId === id ? null : cur));
        return emit({ ...s, order: s.order.filter((x) => x !== id) });
      }
      const anchor = afterId ? s.order.indexOf(afterId) : -1;
      const at = anchor >= 0 ? anchor + 1 : Math.max(1, s.order.length - 1);
      const next = s.order.slice();
      next.splice(at, 0, id);
      const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
      if (v.some((m) => m.level === "error")) return s;
      return emit({ ...s, order: next, collapsed: { ...s.collapsed, [id]: false } });
    });
  }, [byId, emit]);

  const validation = React.useMemo(() => validatePipeline(orderedStages), [orderedStages]);
  const missing = React.useMemo(
    () => addable.filter((id) => !state.order.includes(id)),
    [addable, state.order],
  );

  return {
    state, byId, orderedStages, validation, missing,
    sel, setSel, flash,
    toggleCollapse, toggleOptional, setConfig, getConfig,
    reorder, removeStage, insertStage, toggleStage,
  };
}

export type UsePipelineReturn = ReturnType<typeof usePipeline>;
