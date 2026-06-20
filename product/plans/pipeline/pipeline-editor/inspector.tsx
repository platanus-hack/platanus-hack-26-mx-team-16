"use client";
// inspector.tsx — right-side detail / config panel.
import * as React from "react";
import type { Stage, Phase, ConfigField, Selection, Appearance } from "./types";
import { getAccent, accentVars, type Accent } from "./accents";
import { PipeIcon } from "./icons";
import { ScopeChip } from "./nodes";

function CfgFieldRow({
  f, value, onChange,
}: { f: ConfigField; value: string | number | undefined; onChange: (v: string | number) => void }) {
  const v = value !== undefined ? value : f.value;
  if (f.type === "slider") {
    return (
      <label className="pe-field">
        <div className="pe-flabel"><span>{f.label}</span><span className="pe-fval">{Number(v).toFixed(2)}</span></div>
        <input type="range" className="pe-range" min={f.min} max={f.max} step={f.step} value={v}
          onChange={(e) => onChange(Number(e.target.value))} />
      </label>
    );
  }
  if (f.type === "number") {
    return (
      <label className="pe-field">
        <div className="pe-flabel"><span>{f.label}</span></div>
        <div className="pe-numwrap">
          <input type="number" className="pe-input" value={v} onChange={(e) => onChange(Number(e.target.value))} />
          {f.unit && <span className="pe-unit">{f.unit}</span>}
        </div>
      </label>
    );
  }
  if (f.type === "text") {
    return (
      <label className="pe-field">
        <div className="pe-flabel"><span>{f.label}</span></div>
        <input type="text" className="pe-input" value={v} onChange={(e) => onChange(e.target.value)} />
      </label>
    );
  }
  if (f.type === "segmented") {
    return (
      <div className="pe-field">
        <div className="pe-flabel"><span>{f.label}</span></div>
        <div className="pe-seg">
          {f.options?.map((o) => (
            <button type="button" key={o} className={"pe-seg-b" + (o === v ? " on" : "")} onClick={() => onChange(o)}>{o}</button>
          ))}
        </div>
      </div>
    );
  }
  return (
    <label className="pe-field">
      <div className="pe-flabel"><span>{f.label}</span></div>
      <select className="pe-input pe-select" value={v} onChange={(e) => onChange(e.target.value)}>
        {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

function PhaseConfig({
  stage, phase, getConfig, setConfig,
}: {
  stage: Stage; phase: Phase;
  getConfig: (sid: string, kind: string, key: string) => string | number | undefined;
  setConfig: (sid: string, kind: string, key: string, v: string | number) => void;
}) {
  if (!phase.config || !phase.config.length) {
    return <div className="pe-empty">Esta fase no expone parámetros configurables.</div>;
  }
  return (
    <div className="pe-fields">
      {phase.config.map((f) => (
        <CfgFieldRow key={f.key} f={f}
          value={getConfig(stage.id, phase.kind, f.key)}
          onChange={(val) => setConfig(stage.id, phase.kind, f.key, val)} />
      ))}
    </div>
  );
}

export interface InspectorPanelProps {
  sel: Selection;
  stages: Stage[];
  collapsed: Record<string, boolean>;
  optional: Record<string, boolean>;
  palette: Appearance["palette"];
  getConfig: (sid: string, kind: string, key: string) => string | number | undefined;
  setConfig: (sid: string, kind: string, key: string, v: string | number) => void;
  onClose: () => void;
  onSelect: (sel: { stageId: string; kind?: string }) => void;
  onToggleCollapse: (id: string) => void;
  onToggleOptional: (kind: string) => void;
  onRemoveStage: (id: string) => void;
}

export function InspectorPanel(props: InspectorPanelProps) {
  const { sel, stages, collapsed, optional, palette } = props;
  if (!sel) return null;
  const stage = stages.find((s) => s.id === sel.stageId);
  if (!stage) return null;
  const accent: Accent = getAccent(stage.accent, palette);
  const phase = sel.kind ? stage.phases.find((p) => p.kind === sel.kind) ?? null : null;
  const isGroup = stage.type === "group";

  return (
    <aside className="pe-inspector" style={accentVars(accent)} onMouseDown={(e) => e.stopPropagation()}>
      <div className="pe-insp-head">
        <span className="pe-ico" style={{ color: accent.solid }}>
          <PipeIcon name={phase ? phase.icon : stage.icon} size={20} />
        </span>
        <div className="pe-insp-titles">
          <div className="pe-insp-title">{phase ? phase.label : stage.name}</div>
          <div className="pe-insp-kind">{phase ? phase.kind : `etapa ${stage.num}`}</div>
        </div>
        <button type="button" className="pe-close" onClick={props.onClose} title="Cerrar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>

      <div className="pe-insp-meta">
        <span className="pe-pilltag" style={{ color: accent.text, borderColor: accent.line }}>{stage.tag}</span>
        <ScopeChip scope={(phase ?? stage).scope} />
        {stage.atomic && <span className="pe-flag">par atómico</span>}
      </div>

      <div className="pe-insp-body">
        <p className="pe-desc">{phase ? phase.summary : stage.summary}</p>

        {phase?.when && (
          <div className="pe-rule">
            <span className="pe-rule-k">when</span>
            <code>{phase.when}</code>
            <span className="pe-rule-note">disparada por el gate</span>
          </div>
        )}
        {phase?.sameKind && (
          <div className="pe-kindnote">
            kind <code>{phase.sameKind}</code> compartido — el rol se decide por <code>config.trigger</code>, no por el kind.
          </div>
        )}

        {isGroup && !phase && (
          <>
            <div className="pe-sectlbl">Fases del grupo</div>
            <div className="pe-memlist">
              {stage.phases.map((p) => {
                const off = !!p.optional && optional[p.kind] === false;
                return (
                  <div key={p.kind} className={"pe-mem" + (off ? " off" : "")} onClick={() => props.onSelect({ stageId: stage.id, kind: p.kind })}>
                    <span className="pe-ico sm" style={{ color: accent.solid }}><PipeIcon name={p.icon} size={15} /></span>
                    <div className="pe-mem-main">
                      <span className="pe-mem-name">{p.label}</span>
                      <span className="pe-mem-kind">{p.kind}{p.when ? ` · when ${p.when}` : ""}</span>
                    </div>
                    {p.optional && (
                      <button type="button" className="pe-sw sm" data-on={off ? "0" : "1"}
                        onClick={(e) => { e.stopPropagation(); props.onToggleOptional(p.kind); }} title="Activar / desactivar"><i /></button>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        {phase && (
          <>
            <div className="pe-sectlbl">Configuración</div>
            <PhaseConfig stage={stage} phase={phase} getConfig={props.getConfig} setConfig={props.setConfig} />
            {phase.optional && (
              <div className="pe-optrow">
                <span>Fase opcional</span>
                <button type="button" className="pe-sw" data-on={optional[phase.kind] === false ? "0" : "1"}
                  onClick={() => props.onToggleOptional(phase.kind)}><i /></button>
              </div>
            )}
          </>
        )}

        {!isGroup && !phase && (
          <>
            <div className="pe-sectlbl">Configuración</div>
            <PhaseConfig stage={stage} phase={stage.phases[0]} getConfig={props.getConfig} setConfig={props.setConfig} />
          </>
        )}
      </div>

      <div className="pe-insp-foot">
        {isGroup && (
          <button type="button" className="pe-btn ghost" onClick={() => props.onToggleCollapse(stage.id)}>
            {collapsed[stage.id] ? "Expandir grupo" : "Colapsar grupo"}
          </button>
        )}
        {stage.removable
          ? <button type="button" className="pe-btn danger" onClick={() => props.onRemoveStage(stage.id)}>Quitar etapa</button>
          : <span className="pe-lock">{stage.atomic ? "Se mueve y quita como par" : "Etapa requerida"}</span>}
      </div>
    </aside>
  );
}
