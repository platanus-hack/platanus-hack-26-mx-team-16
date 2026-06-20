"use client";
// nodes.tsx — presentational node components for the spine.
import * as React from "react";
import type { Stage, Phase, Appearance } from "./types";
import type { Block, InnerNode as InnerNodeT, Layout } from "./layout";
import { edgePath } from "./layout";
import { accentVars, type Accent } from "./accents";
import { PipeIcon } from "./icons";

function ScopeChip({ scope }: { scope: Stage["scope"] }) {
  return (
    <span className={"pe-scope pe-scope-" + scope}>
      {scope === "document" ? "documento" : "caso"}
    </span>
  );
}

function Port({ side }: { side: "top" | "bottom" }) {
  return <span className={"pe-port pe-port-" + side} aria-hidden="true" />;
}

function Glyph({ icon, accent, ui }: { icon: Stage["icon"]; accent: Accent; ui: Appearance }) {
  if (!ui.icons) {
    return <span className="pe-dot" style={{ background: accent.solid }} aria-hidden="true" />;
  }
  return (
    <span className="pe-ico" style={{ color: accent.solid }}>
      <PipeIcon name={icon} size={ui.density === "compacto" ? 16 : 18} />
    </span>
  );
}

function RemoveBtn({ stage, onRemove }: { stage: Stage; onRemove?: (id: string) => void }) {
  if (!stage.removable || !onRemove) return null;
  return (
    <button
      type="button"
      className="pe-remove"
      title="Quitar etapa"
      aria-label={"Quitar " + stage.name}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => { e.stopPropagation(); onRemove(stage.id); }}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
    </button>
  );
}

const Chevron = ({ dir }: { dir: "right" | "down" }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={dir === "right" ? "M9 6l6 6-6 6" : "M6 9l6 6 6-6"} />
  </svg>
);

export interface NodeCommon {
  accent: Accent;
  ui: Appearance;
  selected: boolean;
  dragging: boolean;
  onSelect: (sel: { stageId: string; kind?: string }) => void;
  onHandleDown: (e: React.MouseEvent, id: string) => void;
  onToggleCollapse: (id: string) => void;
  onRemove?: (id: string) => void;
}

export function SoloNode({ block, accent, ui, selected, dragging, onSelect, onHandleDown, onRemove }: NodeCommon & { block: Block }) {
  const s = block.stage;
  const phase = s.phases[0];
  const showSum = ui.density !== "compacto" && ui.nodeStyle !== "pastillas";
  const opt = s.removable && s.scope === "case";
  return (
    <div
      className={"pe-card v-" + ui.nodeStyle + (selected ? " is-sel" : "") + (dragging ? " is-drag" : "")}
      style={{ position: "absolute", left: block.x, top: block.y, width: block.w, height: block.h, ...accentVars(accent) }}
      onMouseDown={(e) => onHandleDown(e, s.id)}
      onClick={(e) => { e.stopPropagation(); onSelect({ stageId: s.id }); }}
    >
      <Port side="top" />
      <RemoveBtn stage={s} onRemove={onRemove} />
      <div className="pe-body">
        <Glyph icon={s.icon} accent={accent} ui={ui} />
        <div className="pe-main">
          <div className="pe-titlerow">
            <span className="pe-num" style={{ color: accent.text, background: accent.soft }}>{s.num}</span>
            <span className="pe-name">{s.name}</span>
            {opt && <span className="pe-optchip">opcional</span>}
            <ScopeChip scope={s.scope} />
          </div>
          <div className="pe-kind">{phase.kind}</div>
          {showSum && <div className="pe-sum">{s.summary}</div>}
        </div>
      </div>
      <Port side="bottom" />
    </div>
  );
}

export function CollapsedGroup({ block, accent, ui, selected, dragging, onSelect, onHandleDown, onToggleCollapse, onRemove }: NodeCommon & { block: Block }) {
  const s = block.stage;
  const opt = s.removable && s.scope === "case";
  return (
    <div
      className={"pe-card pe-grp-collapsed v-" + ui.nodeStyle + (selected ? " is-sel" : "") + (dragging ? " is-drag" : "")}
      style={{ position: "absolute", left: block.x, top: block.y, width: block.w, height: block.h, ...accentVars(accent) }}
      onMouseDown={(e) => onHandleDown(e, s.id)}
      onClick={(e) => { e.stopPropagation(); onSelect({ stageId: s.id }); }}
    >
      <Port side="top" />
      <RemoveBtn stage={s} onRemove={onRemove} />
      <div className="pe-body">
        <Glyph icon={s.icon} accent={accent} ui={ui} />
        <div className="pe-main">
          <div className="pe-titlerow">
            <span className="pe-num" style={{ color: accent.text, background: accent.soft }}>{s.num}</span>
            <span className="pe-name">{s.name}</span>
            {opt && <span className="pe-optchip">opcional</span>}
            <ScopeChip scope={s.scope} />
          </div>
          <div className="pe-grpmeta">
            <span className="pe-pilltag" style={{ color: accent.text, borderColor: accent.line }}>
              {s.phases.length} fases · {s.atomic ? "par atómico" : "grupo"}
            </span>
            <span className="pe-minidots">
              {s.phases.map((p) => <i key={p.kind} style={{ background: accent.line }} />)}
            </span>
          </div>
        </div>
        <button type="button" className="pe-chev" title="Expandir grupo" style={{ color: accent.text }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onToggleCollapse(s.id); }}>
          <Chevron dir="right" />
        </button>
      </div>
      <Port side="bottom" />
    </div>
  );
}

export function GroupBox({ block, accent, ui, selected, dragging, onSelect, onHandleDown, onToggleCollapse, onRemove }: NodeCommon & { block: Block }) {
  const s = block.stage;
  const opt = s.removable && s.scope === "case";
  return (
    <div
      className={"pe-group v-" + ui.nodeStyle + (selected ? " is-sel" : "") + (dragging ? " is-drag" : "")}
      style={{ position: "absolute", left: block.x, top: block.y, width: block.w, height: block.h, ...accentVars(accent) }}
      onMouseDown={(e) => onHandleDown(e, s.id)}
      onClick={(e) => { e.stopPropagation(); onSelect({ stageId: s.id }); }}
    >
      <Port side="top" />
      <RemoveBtn stage={s} onRemove={onRemove} />
      <div className="pe-ghead" style={{ height: ui.density === "compacto" ? 42 : 50 }}>
        <Glyph icon={s.icon} accent={accent} ui={ui} />
        <span className="pe-num" style={{ color: accent.text, background: accent.soft }}>{s.num}</span>
        <span className="pe-name">{s.name}</span>
        {opt && <span className="pe-optchip">opcional</span>}
        <span className="pe-gcount">{s.phases.length} fases</span>
        <ScopeChip scope={s.scope} />
        <button type="button" className="pe-chev" title="Colapsar grupo" style={{ color: accent.text }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onToggleCollapse(s.id); }}>
          <Chevron dir="down" />
        </button>
      </div>
      <Port side="bottom" />
    </div>
  );
}

export interface InnerNodeProps {
  node: InnerNodeT & { stageId: string };
  accent: Accent;
  ui: Appearance;
  selected: boolean;
  disabled: boolean;
  onSelect: (sel: { stageId: string; kind?: string }) => void;
  onToggleOptional: (kind: string) => void;
}

export function InnerNode({ node, accent, ui, selected, disabled, onSelect, onToggleOptional }: InnerNodeProps) {
  const p: Phase = node.phase;
  return (
    <div
      className={"pe-inner v-" + ui.nodeStyle + (selected ? " is-sel" : "") + (disabled ? " is-off" : "") + (p.branch ? " is-branch" : "")}
      style={{ position: "absolute", left: node.x, top: node.y, width: node.w, height: node.h, ...accentVars(accent) }}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => { e.stopPropagation(); onSelect({ stageId: node.stageId, kind: p.kind }); }}
    >
      <Glyph icon={p.icon} accent={accent} ui={ui} />
      <div className="pe-imain">
        <div className="pe-ilabel">
          <span className="pe-iname">{p.label}</span>
          {p.optional && <span className="pe-opt">opcional</span>}
        </div>
        <div className="pe-ikind">{p.kind}{p.when && <span className="pe-when">when {p.when}</span>}</div>
      </div>
      {p.optional && (
        <button type="button" className="pe-sw" data-on={disabled ? "0" : "1"}
          title={disabled ? "Activar fase" : "Desactivar fase"}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onToggleOptional(p.kind); }}>
          <i />
        </button>
      )}
    </div>
  );
}

export function PipeEdges({ layout, ui }: { layout: Layout; ui: Appearance }) {
  const innerEdges: { x1: number; y1: number; x2: number; y2: number; branch?: boolean }[] = [];
  layout.blocks.forEach((b) => { if (b.inner) b.inner.edges.forEach((e) => innerEdges.push(e)); });
  return (
    <svg className="pe-edges" width={layout.worldW} height={layout.worldH}
      style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none", overflow: "visible" }}>
      <defs>
        <marker id="peArr" viewBox="0 0 10 10" refX="7.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
          <path d="M0 1 L8 5 L0 9" fill="none" stroke="var(--pe-edge)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </marker>
      </defs>
      {layout.edges.map((e, i) => (
        <path key={"e" + i} d={edgePath(e, ui.edgeStyle)} fill="none"
          stroke="var(--pe-edge)" strokeWidth="1.8" markerEnd="url(#peArr)"
          strokeDasharray={e.crossScope ? "5 4" : "none"} opacity={e.crossScope ? 0.7 : 1} />
      ))}
      {innerEdges.map((e, i) => (
        <path key={"i" + i} d={edgePath(e, ui.edgeStyle)} fill="none"
          stroke="var(--pe-edge-soft)" strokeWidth="1.5"
          strokeDasharray={e.branch ? "4 3" : "none"} />
      ))}
    </svg>
  );
}

export { ScopeChip };
