"use client";
// pipeline-editor.tsx — main component. Vertical-scroll spine editor.
//
//   import { PipelineEditor } from "@/components/pipeline-editor";
//   <PipelineEditor />                      // uncontrolled, sample data
//   <PipelineEditor stages={myStages} initialState={myState}
//                   appearance={{ density: "compacto" }}
//                   onChange={(s) => save(s)} />
//
import * as React from "react";
import "./pipeline-editor.css";
import type {
  Stage, PipelineState, Selection, Appearance,
} from "./types";
import { DEFAULT_APPEARANCE } from "./types";
import { computeLayout, type Block } from "./layout";
import { getAccent } from "./accents";
import { PipeIcon } from "./icons";
import { usePipeline } from "./use-pipeline";
import {
  SoloNode, CollapsedGroup, GroupBox, InnerNode, PipeEdges, ScopeChip,
  type NodeCommon,
} from "./nodes";
import { InspectorPanel } from "./inspector";
import { SAMPLE_STAGES, SAMPLE_INITIAL_STATE, SAMPLE_ADDABLE } from "./sample-data";

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export interface PipelineEditorProps {
  /** Full stage catalog. Defaults to the bundled sample. */
  stages?: Stage[];
  /** Initial spine + collapse + optional + config. */
  initialState?: PipelineState;
  /** Stage ids insertable from the "+" menu. Defaults to all removable stages. */
  addable?: string[];
  /** Visual options (replaces the prototype's Tweaks panel). */
  appearance?: Partial<Appearance>;
  /** Show the top toolbar (validation chip + quality-control toggle). */
  showToolbar?: boolean;
  /** Id of a toggleable group wired to the toolbar switch (e.g. "calidad"). */
  toggleableStageId?: string;
  /** Insert the toggleable stage right after this id. */
  toggleAfterId?: string;
  className?: string;
  style?: React.CSSProperties;
  onChange?: (state: PipelineState) => void;
  onSelect?: (sel: Selection) => void;
}

export function PipelineEditor({
  stages = SAMPLE_STAGES,
  initialState = SAMPLE_INITIAL_STATE,
  addable = SAMPLE_ADDABLE,
  appearance,
  showToolbar = true,
  toggleableStageId = "calidad",
  toggleAfterId = "completitud",
  className,
  style,
  onChange,
  onSelect,
}: PipelineEditorProps) {
  const ui: Appearance = { ...DEFAULT_APPEARANCE, ...appearance };

  const p = usePipeline({ stages, initialState, addable, onChange, onSelect });
  const { state, orderedStages, validation, missing, sel, setSel, flash } = p;

  const layout = React.useMemo(
    () => computeLayout(orderedStages, { collapsed: state.collapsed, density: ui.density }),
    [orderedStages, state.collapsed, ui.density],
  );
  const accentOf = React.useCallback((s: Stage) => getAccent(s.accent, ui.palette), [ui.palette]);

  const worldRef = React.useRef<HTMLDivElement>(null);
  const layoutRef = React.useRef(layout); layoutRef.current = layout;

  const [dragId, setDragId] = React.useState<string | null>(null);
  const [drop, setDrop] = React.useState<{ idx: number; dy: number } | null>(null);
  const [addMenu, setAddMenu] = React.useState<{ at: number; wx: number; wy: number } | null>(null);
  const dragRef = React.useRef<{ id: string; idx: number; dy: number } | null>(null);

  const onCanvasClick = (e: React.MouseEvent) => {
    if (!(e.target as HTMLElement).closest(".pe-card,.pe-group,.pe-inner,.pe-addbtn,.pe-inspector,.pe-addmenu")) {
      setSel(null); setAddMenu(null);
    }
  };

  const onHandleDown = (e: React.MouseEvent, id: string) => {
    if (e.button !== 0) return;
    const sy = e.clientY, sx = e.clientX;
    let active = false;
    const move = (ev: MouseEvent) => {
      if (!active && Math.abs(ev.clientY - sy) + Math.abs(ev.clientX - sx) < 6) return;
      if (!active) { active = true; setDragId(id); setAddMenu(null); }
      const L = layoutRef.current;
      const w = worldRef.current;
      if (!w) return;
      const r = w.getBoundingClientRect();
      const worldY = ev.clientY - r.top;
      let idx = 0;
      for (const b of L.blocks) if (worldY > b.y + b.h / 2) idx++;
      dragRef.current = { id, idx, dy: ev.clientY - sy };
      setDrop({ idx, dy: ev.clientY - sy });
    };
    const up = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
      const d = dragRef.current; dragRef.current = null; setDragId(null); setDrop(null);
      if (!active || !d) return;
      p.reorder(id, d.idx);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  const vState =
    validation.find((m) => m.level === "error") ??
    validation.find((m) => m.level === "warn") ??
    validation[0];

  // ── blocks ─────────────────────────────────────────────────────────────────
  const blockEls = layout.blocks.map((b) => {
    const accent = accentOf(b.stage);
    const isSel = !!sel && sel.stageId === b.id && !sel.kind;
    const dragging = dragId === b.id;
    const wrapStyle: React.CSSProperties = dragging
      ? { transform: `translateY(${drop ? drop.dy : 0}px)`, zIndex: 50 }
      : {};
    const common = {
      accent, ui, selected: isSel, dragging,
      onSelect: setSel, onHandleDown, onToggleCollapse: p.toggleCollapse, onRemove: p.removeStage,
    };
    if (b.isGroup && !b.collapsed && b.inner) {
      return (
        <div key={b.id} style={{ position: "absolute", inset: 0, ...wrapStyle, pointerEvents: dragging ? "none" : "auto" }}>
          <GroupBox block={b} {...common} />
          {b.inner.nodes.map((n) => {
            const off = !!n.phase.optional && state.optional[n.phase.kind] === false;
            const nodeSel = !!sel && sel.stageId === b.id && sel.kind === n.phase.kind;
            return (
              <InnerNode key={n.phase.kind} node={{ ...n, stageId: b.id }} accent={accent} ui={ui}
                selected={nodeSel} disabled={off} onSelect={setSel} onToggleOptional={p.toggleOptional} />
            );
          })}
        </div>
      );
    }
    const Comp = (b.isGroup ? CollapsedGroup : SoloNode) as React.FC<NodeCommon & { block: Block }>;
    return (
      <div key={b.id} style={{ position: "absolute", inset: 0, ...wrapStyle }}>
        <Comp block={b} {...common} />
      </div>
    );
  });

  const addEls = layout.edges.map((e) => (
    <button type="button" key={"add" + e.idx} className="pe-addbtn"
      style={{ left: e.x1, top: (e.y1 + e.y2) / 2 }} title="Insertar etapa aquí"
      onMouseDown={(ev) => ev.stopPropagation()}
      onClick={(ev) => {
        ev.stopPropagation();
        setAddMenu(addMenu && addMenu.at === e.idx + 1 ? null : { at: e.idx + 1, wx: e.x1, wy: (e.y1 + e.y2) / 2 });
      }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
    </button>
  ));

  let dropIndicator: React.ReactNode = null;
  if (dragId && drop) {
    const L = layout; const i = drop.idx;
    let y: number;
    if (i <= 0) y = L.blocks[0].y - L.D.blockGap / 2;
    else if (i >= L.blocks.length) {
      const last = L.blocks[L.blocks.length - 1];
      y = last.y + last.h + L.D.blockGap / 2;
    } else y = (L.blocks[i - 1].y + L.blocks[i - 1].h + L.blocks[i].y) / 2;
    dropIndicator = <div className="pe-drop" style={{ left: L.CX - 190, top: y, width: 380 }} />;
  }

  return (
    <div className={"pe-root" + (className ? " " + className : "")} style={style}>
      {showToolbar && (
        <header className="pe-hd">
          <div className="pe-brand">
            <span className="pe-logo">◆</span>
            <span className="pe-bc-cur">Editor de pipeline</span>
          </div>
          <div className={"pe-vchip " + vState.level} title={validation.map((m) => m.msg).join("\n")}>
            <span className="pe-vdot" />
            {vState.level === "error" ? "Pipeline inválido" : vState.level === "warn" ? "Aviso de orden" : "Pipeline válido"}
            {validation.length > 1 && <span className="pe-vct">{validation.length}</span>}
          </div>
          <div className="pe-hd-right">
            {toggleableStageId && (
              <div className="pe-qc">
                <span>Control de calidad</span>
                <button type="button" className="pe-toggle" data-on={state.order.includes(toggleableStageId) ? "1" : "0"}
                  onClick={() => p.toggleStage(toggleableStageId, toggleAfterId)}
                  title="Activar / desactivar grupo">
                  <i />
                </button>
              </div>
            )}
          </div>
        </header>
      )}

      <div className={"pe-vp bg-" + ui.background} onClick={onCanvasClick}>
        <div ref={worldRef} className="pe-world" data-d={ui.density} data-ns={ui.nodeStyle}
          style={{ width: layout.worldW, height: layout.worldH }}>
          {layout.frontierY != null && (
            <div className="pe-frontier" style={{ top: layout.frontierY, left: 40, width: layout.worldW - 80 }}>
              <span className="pe-frontier-lbl">frontera de scope · documento ▲ · caso ▼</span>
            </div>
          )}
          <PipeEdges layout={layout} ui={ui} />
          {dropIndicator}
          {blockEls}
          {addEls}

          {addMenu && (
            <div className="pe-addmenu"
              style={{ left: clamp(addMenu.wx + 6, 6, layout.worldW - 230), top: addMenu.wy + 6 }}
              onMouseDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
              <div className="pe-addmenu-h">Insertar etapa</div>
              {missing.length ? missing.map((id) => {
                const s = p.byId[id]; const a = accentOf(s);
                return (
                  <button type="button" key={id} className="pe-addmenu-i" onClick={() => { p.insertStage(id, addMenu.at); setAddMenu(null); }}>
                    <span className="pe-ico sm" style={{ color: a.solid }}><PipeIcon name={s.icon} size={15} /></span>
                    <span className="pe-addmenu-name">{s.name}</span>
                    <ScopeChip scope={s.scope} />
                  </button>
                );
              }) : <div className="pe-addmenu-empty">Todas las etapas ya están en el pipeline.</div>}
            </div>
          )}
        </div>

        {flash && <div className="pe-flash">{flash}</div>}
      </div>

      <InspectorPanel
        sel={sel}
        stages={stages}
        collapsed={state.collapsed}
        optional={state.optional}
        palette={ui.palette}
        getConfig={p.getConfig}
        setConfig={p.setConfig}
        onClose={() => setSel(null)}
        onSelect={setSel}
        onToggleCollapse={p.toggleCollapse}
        onToggleOptional={p.toggleOptional}
        onRemoveStage={p.removeStage}
      />
    </div>
  );
}

export default PipelineEditor;
