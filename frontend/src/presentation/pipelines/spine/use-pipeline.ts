"use client";
// use-pipeline.ts — state hook. Manages spine order, collapse, optional toggles,
// config overrides and selection. Uncontrolled by default; emits `onChange`.
import * as React from "react";
import { validatePipeline } from "./layout";
import type { PipelineState, Selection, Stage } from "./types";

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
    () =>
      Object.fromEntries(stages.map((s) => [s.id, s])) as Record<string, Stage>,
    [stages]
  );
  const addable = React.useMemo(
    () => opts.addable ?? stages.filter((s) => s.removable).map((s) => s.id),
    [opts.addable, stages]
  );

  const [state, setState] = React.useState<PipelineState>(initialState);
  const [sel, setSelInternal] = React.useState<Selection>(null);
  const [flash, setFlash] = React.useState<string | null>(null);
  const flashTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // `onChange` se emite en un effect TRAS el commit, no dentro del updater de
  // setState: emitir en el updater dispara un setState del store mientras React
  // renderiza este componente y el cambio se pierde. El host ignora el no-op
  // (compara la receta), así que emitir también al colapsar es inofensivo.
  const onChangeRef = React.useRef(onChange);
  onChangeRef.current = onChange;
  // Guard por IDENTIDAD (no por un flag "mounted"): bajo StrictMode el effect se
  // doble-invoca en el mount y un ref booleano no se resetea ⇒ emitiría el estado
  // inicial y machacaría la receta. Mientras `state` siga siendo el inicial no
  // hay cambio del usuario que emitir.
  const initialRef = React.useRef(state);
  React.useEffect(() => {
    if (state === initialRef.current) return;
    onChangeRef.current?.(state);
  }, [state]);

  const update = React.useCallback(
    (fn: (s: PipelineState) => PipelineState) => setState(fn),
    []
  );

  const setSel = React.useCallback(
    (s: Selection) => {
      setSelInternal(s);
      onSelect?.(s);
    },
    [onSelect]
  );

  const doFlash = React.useCallback((msg: string) => {
    setFlash(msg);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setFlash(null), 2600);
  }, []);
  React.useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current);
    },
    []
  );

  const orderedStages = React.useMemo(
    () => state.order.map((id) => byId[id]).filter(Boolean),
    [state.order, byId]
  );

  // ── structural actions ────────────────────────────────────────────────────
  // Colapsar es solo UI: aunque cambie el estado (y por tanto emita onChange),
  // no toca la receta, así que el host lo descarta como no-op (no marca dirty).
  const toggleCollapse = React.useCallback((id: string) => {
    setState((s) => ({
      ...s,
      collapsed: { ...s.collapsed, [id]: !s.collapsed[id] },
    }));
  }, []);

  const toggleOptional = React.useCallback(
    (kind: string) => {
      update((s) => ({
        ...s,
        optional: { ...s.optional, [kind]: s.optional[kind] === false },
      }));
    },
    [update]
  );

  const setConfig = React.useCallback(
    (stageId: string, kind: string, key: string, value: string | number) => {
      update((s) => ({
        ...s,
        config: {
          ...s.config,
          [stageId]: {
            ...(s.config[stageId] ?? {}),
            [kind]: {
              ...((s.config[stageId] ?? {})[kind] ?? {}),
              [key]: value,
            },
          },
        },
      }));
    },
    [update]
  );
  const getConfig = React.useCallback(
    (stageId: string, kind: string, key: string): string | number | undefined =>
      state.config[stageId]?.[kind]?.[key],
    [state.config]
  );

  const reorder = React.useCallback(
    (id: string, targetIdx: number) => {
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
          doFlash(
            "No se puede: rompería la frontera de scope (documento → caso)."
          );
          return s;
        }
        return { ...s, order: next };
      });
    },
    [byId, doFlash]
  );

  const removeStage = React.useCallback(
    (id: string) => {
      update((s) => ({ ...s, order: s.order.filter((x) => x !== id) }));
      setSelInternal((cur) => (cur && cur.stageId === id ? null : cur));
    },
    [update]
  );

  const insertStage = React.useCallback(
    (id: string, atIdx: number) => {
      setState((s) => {
        if (s.order.includes(id)) return s;
        const next = s.order.slice();
        next.splice(atIdx, 0, id);
        const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
        if (v.some((m) => m.level === "error")) {
          doFlash("Esa posición rompería la frontera de scope.");
          return s;
        }
        return { ...s, order: next };
      });
    },
    [byId, doFlash]
  );

  /** Toggle a toggleable group (e.g. quality control) in/out of the spine. */
  const toggleStage = React.useCallback(
    (id: string, afterId?: string) => {
      setState((s) => {
        if (s.order.includes(id)) {
          setSelInternal((cur) => (cur && cur.stageId === id ? null : cur));
          return { ...s, order: s.order.filter((x) => x !== id) };
        }
        const anchor = afterId ? s.order.indexOf(afterId) : -1;
        const at = anchor >= 0 ? anchor + 1 : Math.max(1, s.order.length - 1);
        const next = s.order.slice();
        next.splice(at, 0, id);
        const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
        if (v.some((m) => m.level === "error")) return s;
        return {
          ...s,
          order: next,
          collapsed: { ...s.collapsed, [id]: false },
        };
      });
    },
    [byId]
  );

  // ── case scope (en bloque) ─────────────────────────────────────────────────
  // Un workflow es straight-through (solo document-scope; finalize cierra cada
  // archivo como su propio caso) o basado-en-caso (acumula en un expediente y
  // output/deliver lo cierra). Estas dos acciones agregan/quitan TODO el scope de
  // caso de una vez, en lugar de etapa por etapa con el menú «+».
  const hasCaseScope = React.useMemo(
    () => orderedStages.some((s) => s.scope === "case"),
    [orderedStages]
  );

  // Esqueleto mínimo del scope de caso, DERIVADO del catálogo (no hardcodeado):
  // la primera etapa case-scope por rank (entrada del expediente) + toda etapa
  // case-scope no removible (el cierre, p. ej. Salida). Para el spine de Doxiq
  // esto es Completitud (await_documents) + Salida (output/deliver).
  const caseSkeleton = React.useMemo(() => {
    const caseStages = stages
      .filter((s) => s.scope === "case")
      .sort((a, b) => a.rank - b.rank);
    const ids: string[] = [];
    if (caseStages[0]) ids.push(caseStages[0].id);
    for (const s of caseStages) if (!s.removable) ids.push(s.id);
    return Array.from(new Set(ids));
  }, [stages]);

  const addCaseScope = React.useCallback(() => {
    setState((s) => {
      const have = new Set(s.order);
      const toAdd = caseSkeleton.filter((id) => !have.has(id));
      if (!toAdd.length) return s;
      // El orden de la receta es siempre rank-ascendente (lo exige
      // validatePipeline); reordenar por rank deja las etapas nuevas en su sitio
      // canónico sin tocar la posición relativa de las existentes.
      const next = [...s.order, ...toAdd].sort(
        (a, b) => (byId[a]?.rank ?? 0) - (byId[b]?.rank ?? 0)
      );
      const v = validatePipeline(next.map((x) => byId[x]).filter(Boolean));
      if (v.some((m) => m.level === "error")) {
        doFlash("No se pudo agregar el scope de caso.");
        return s;
      }
      return { ...s, order: next };
    });
  }, [caseSkeleton, byId, doFlash]);

  // Suelta TODAS las etapas case-scope, incluida Salida (que la × por-etapa
  // bloquea con removable:false): el resultado es straight-through, con finalize
  // cerrando cada documento.
  const removeCaseScope = React.useCallback(() => {
    update((s) => ({
      ...s,
      order: s.order.filter((id) => byId[id]?.scope !== "case"),
    }));
    setSelInternal((cur) =>
      cur && byId[cur.stageId]?.scope === "case" ? null : cur
    );
  }, [byId, update]);

  const validation = React.useMemo(
    () => validatePipeline(orderedStages),
    [orderedStages]
  );
  const missing = React.useMemo(
    () => addable.filter((id) => !state.order.includes(id)),
    [addable, state.order]
  );

  return {
    state,
    byId,
    orderedStages,
    validation,
    missing,
    sel,
    setSel,
    flash,
    hasCaseScope,
    toggleCollapse,
    toggleOptional,
    setConfig,
    getConfig,
    reorder,
    removeStage,
    insertStage,
    toggleStage,
    addCaseScope,
    removeCaseScope,
  };
}

export type UsePipelineReturn = ReturnType<typeof usePipeline>;
