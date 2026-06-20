// types.ts — domain model + appearance types for the Pipeline Editor.
// Pure types, no runtime. Swap `Stage[]` for your own data source.

export type Scope = "document" | "case";
export type StageType = "group" | "solo";
export type StageLayout = "stack" | "branch";
export type AccentName = "teal" | "amber" | "gold" | "violet" | "blue" | "rose";

export type FieldType = "select" | "number" | "text" | "slider" | "segmented";

export interface ConfigField {
  key: string;
  type: FieldType;
  label: string;
  value: string | number;
  options?: string[];
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
}

export interface Phase {
  /** Engine kind, e.g. "ingest", "extraction_gate". */
  kind: string;
  label: string;
  icon: IconName;
  scope: Scope;
  summary: string;
  /**
   * Id de la fase REAL del backend cuando la etapa está activa. Lo usa el host
   * para abrir el editor de configuración de esa fase (Doxiq: PhaseDrawer).
   * Ausente en fases plantilla (etapa inactiva / opcional apagada).
   */
  realId?: string;
  /** Optional phase — can be toggled on/off without removing the stage. */
  optional?: boolean;
  /** Renders as a dashed branch consumer under the gate. */
  branch?: boolean;
  role?: string;
  /** Shared engine kind note (e.g. approval = human_review). */
  sameKind?: string;
  config?: ConfigField[];
}

export interface Stage {
  id: string;
  /** Display number, e.g. "1".."7". */
  num: string;
  /**
   * Orden canónico de la etapa (índice). Las capacidades de caso tienen un orden
   * fijo (espejo de capability_macros): el spine solo permite insertar/mover una
   * etapa si mantiene los `rank` en orden ascendente.
   */
  rank: number;
  name: string;
  type: StageType;
  scope: Scope;
  accent: AccentName;
  tag: string;
  layout: StageLayout;
  summary: string;
  /** Whether the user can delete this stage from the spine. */
  removable: boolean;
  /** Whether it can be toggled from a toolbar (e.g. quality control). */
  toggleable?: boolean;
  /** Atomic pair — moves/removes as a unit (e.g. output + deliver). */
  atomic?: boolean;
  icon: IconName;
  phases: Phase[];
}

// ── Appearance (driven by props, replaces the prototype's Tweaks panel) ──────
export type NodeStyle = "tarjetas" | "lineas" | "pastillas";
export type Density = "comodo" | "compacto";
export type EdgeStyle = "bezier" | "step";
export type Palette = "multicolor" | "grafito";
export type Background = "plano" | "cuadricula";

export interface Appearance {
  nodeStyle: NodeStyle;
  density: Density;
  icons: boolean;
  edgeStyle: EdgeStyle;
  palette: Palette;
  background: Background;
}

export const DEFAULT_APPEARANCE: Appearance = {
  nodeStyle: "tarjetas",
  density: "comodo",
  icons: true,
  edgeStyle: "bezier",
  palette: "multicolor",
  background: "plano",
};

// ── Editor state ─────────────────────────────────────────────────────────────
export type ConfigOverrides = Record<
  string,
  Record<string, Record<string, string | number>>
>;

export interface PipelineState {
  /** Stage ids in spine order. */
  order: string[];
  /** Group id → collapsed. */
  collapsed: Record<string, boolean>;
  /** Optional phase kind → enabled. */
  optional: Record<string, boolean>;
  /** Per-stage, per-phase, per-field config overrides. */
  config: ConfigOverrides;
}

export type Selection = { stageId: string; kind?: string; id?: string } | null;

export type ValidationLevel = "ok" | "warn" | "error";
export interface ValidationMessage {
  level: ValidationLevel;
  msg: string;
}

// Icon name union — keep in sync with icons.tsx
export type IconName =
  | "ingest"
  | "extract_text"
  | "classify_pages"
  | "extract_fields"
  | "assess"
  | "validate_extraction"
  | "finalize"
  | "await_documents"
  | "extraction_gate"
  | "await_clarification"
  | "enrich"
  | "analyze"
  | "approval"
  | "output"
  | "deliver";
