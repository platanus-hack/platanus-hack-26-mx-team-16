// layout.ts — pure vertical-spine layout engine + scope validation.
// No DOM, no React. Produces absolute coordinates for a centered scroll column.
import type { Density, Phase, Stage, ValidationMessage } from "./types";

export interface Dims {
  soloW: number;
  groupW: number;
  soloH: number;
  collapsedH: number;
  innerH: number;
  headerH: number;
  innerGap: number;
  pad: number;
  blockGap: number;
  branchGap: number;
  cx: number;
}

export const DIMS: Record<Density, Dims> = {
  comodo: {
    soloW: 376,
    groupW: 432,
    soloH: 78,
    collapsedH: 92,
    innerH: 58,
    headerH: 50,
    innerGap: 12,
    pad: 16,
    blockGap: 64,
    branchGap: 18,
    cx: 330,
  },
  compacto: {
    soloW: 328,
    groupW: 384,
    soloH: 60,
    collapsedH: 74,
    innerH: 46,
    headerH: 42,
    innerGap: 9,
    pad: 13,
    blockGap: 46,
    branchGap: 14,
    cx: 300,
  },
};

export interface InnerNode {
  /** Id estable por posición (`${stageId}::${idx}`) para medir su DOM. */
  id: string;
  phase: Phase;
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface InnerEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  branch?: boolean;
  mini?: boolean;
}
export interface Block {
  id: string;
  stage: Stage;
  x: number;
  y: number;
  w: number;
  h: number;
  collapsed: boolean;
  isGroup: boolean;
  inner: { nodes: InnerNode[]; edges: InnerEdge[]; height: number } | null;
}
export interface Edge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  from: string;
  to: string;
  idx: number;
  crossScope: boolean;
}
export interface Layout {
  blocks: Block[];
  edges: Edge[];
  frontierY: number | null;
  frontierIdx: number;
  worldW: number;
  worldH: number;
  CX: number;
  D: Dims;
}

export interface LayoutUI {
  collapsed: Record<string, boolean>;
  density: Density;
  /**
   * Alturas reales medidas del DOM, por id de nodo/etapa. Las cards crecen con
   * su contenido (`height: auto`) y el motor usa estas medidas para posicionar;
   * sin medida aún, cae al valor por defecto de `Dims` (primer render).
   */
  heights?: Record<string, number>;
  /**
   * Ancho objetivo del "mundo" (px). Cuando es menor que el ancho natural
   * (`cx*2`), el motor recalcula `cx` y los anchos de tarjeta para LLENAR ese
   * ancho a escala 1 (texto a tamaño normal, con wrap) — usado en móvil para que
   * las cards ocupen todo el ancho sin scroll horizontal ni encoger el texto.
   * Sin valor (o ≥ natural) → dims fijas (desktop intacto).
   */
  fitWidth?: number;
}

function layoutInner(
  stage: Stage,
  bx: number,
  by: number,
  bw: number,
  D: Dims,
  heights: Record<string, number>
) {
  const contentX = bx + D.pad;
  const contentW = bw - D.pad * 2;
  let cy = by + D.headerH;
  const nodes: InnerNode[] = [];
  const edges: InnerEdge[] = [];
  const hOf = (id: string, fallback: number) => heights[id] ?? fallback;

  if (stage.layout === "branch") {
    const gate = stage.phases[0];
    const gateId = `${stage.id}::0`;
    const gateNode: InnerNode = {
      id: gateId,
      phase: gate,
      x: contentX,
      y: cy,
      w: contentW,
      h: hOf(gateId, D.innerH),
    };
    nodes.push(gateNode);
    cy += gateNode.h + D.branchGap + 8;
    const branches = stage.phases.slice(1);
    const bw2 = (contentW - D.innerGap) / 2;
    let rowH = 0;
    branches.forEach((p, i) => {
      const id = `${stage.id}::${i + 1}`;
      const nx = contentX + i * (bw2 + D.innerGap);
      const n: InnerNode = {
        id,
        phase: p,
        x: nx,
        y: cy,
        w: bw2,
        h: hOf(id, D.innerH + 6),
      };
      nodes.push(n);
      rowH = Math.max(rowH, n.h);
      edges.push({
        x1: gateNode.x + gateNode.w / 2,
        y1: gateNode.y + gateNode.h,
        x2: n.x + n.w / 2,
        y2: n.y,
        branch: true,
      });
    });
    cy += rowH + D.pad;
  } else {
    stage.phases.forEach((p, i) => {
      const id = `${stage.id}::${i}`;
      const n: InnerNode = {
        id,
        phase: p,
        x: contentX,
        y: cy,
        w: contentW,
        h: hOf(id, D.innerH),
      };
      nodes.push(n);
      if (i > 0) {
        const prev = nodes[i - 1];
        edges.push({
          x1: prev.x + prev.w / 2,
          y1: prev.y + prev.h,
          x2: n.x + n.w / 2,
          y2: n.y,
          mini: true,
        });
      }
      cy += n.h + D.innerGap;
    });
    cy = cy - D.innerGap + D.pad;
  }
  return { nodes, edges, height: cy - by };
}

export function computeLayout(orderedStages: Stage[], ui: LayoutUI): Layout {
  const baseD = DIMS[ui.density] ?? DIMS.comodo;
  const heights = ui.heights ?? {};

  // Ancho fluido: si `fitWidth` es menor que el ancho natural (cx*2), recalculamos
  // el centro y los anchos de tarjeta para que las cards LLENEN ese ancho (a
  // escala 1, sin encoger texto). El resto de dims (alto, paddings, gaps) se
  // mantienen. En desktop (sin fitWidth o ≥ natural) las dims quedan intactas.
  let D = baseD;
  const naturalWorldW = baseD.cx * 2;
  if (ui.fitWidth && ui.fitWidth < naturalWorldW) {
    const EDGE = 14; // margen lateral mínimo de la card respecto al borde del mundo
    const worldW = Math.max(260, ui.fitWidth);
    const cardW = worldW - EDGE * 2;
    D = { ...baseD, cx: worldW / 2, groupW: cardW, soloW: cardW };
  }

  const CX = D.cx;
  let y = 56;
  const blocks: Block[] = [];

  orderedStages.forEach((stage) => {
    const isGroup = stage.type === "group";
    const collapsed = isGroup ? !!ui.collapsed[stage.id] : false;
    const w = isGroup ? D.groupW : D.soloW;
    const x = CX - w / 2;
    let h: number;
    let inner: Block["inner"] = null;
    if (isGroup && !collapsed) {
      inner = layoutInner(stage, x, y, w, D, heights);
      h = inner.height;
    } else if (isGroup) {
      h = heights[stage.id] ?? D.collapsedH;
    } else {
      h = heights[stage.id] ?? D.soloH;
    }
    blocks.push({ id: stage.id, stage, x, y, w, h, collapsed, isGroup, inner });
    y += h + D.blockGap;
  });

  const edges: Edge[] = [];
  for (let i = 0; i < blocks.length - 1; i++) {
    const a = blocks[i],
      b = blocks[i + 1];
    edges.push({
      x1: CX,
      y1: a.y + a.h,
      x2: CX,
      y2: b.y,
      from: a.id,
      to: b.id,
      idx: i,
      crossScope: a.stage.scope !== b.stage.scope,
    });
  }

  let frontierY: number | null = null;
  let frontierIdx = -1;
  for (let i = 0; i < blocks.length - 1; i++) {
    if (
      blocks[i].stage.scope === "document" &&
      blocks[i + 1].stage.scope === "case"
    ) {
      frontierY = (blocks[i].y + blocks[i].h + blocks[i + 1].y) / 2;
      frontierIdx = i;
    }
  }

  return {
    blocks,
    edges,
    frontierY,
    frontierIdx,
    worldW: CX * 2,
    worldH: y + 24,
    CX,
    D,
  };
}

/** Hard scope frontier + soft ordering recommendations. */
export function validatePipeline(orderedStages: Stage[]): ValidationMessage[] {
  const msgs: ValidationMessage[] = [];
  let seenCase = false;
  let broken = false;
  for (const s of orderedStages) {
    if (s.scope === "case") seenCase = true;
    else if (s.scope === "document" && seenCase) broken = true;
  }
  if (broken) {
    msgs.push({
      level: "error",
      msg: "Frontera de scope rota: una fase document-scope quedó por debajo de una case-scope.",
    });
  }
  // Orden canónico: los `rank` deben ir estrictamente ascendentes. Esto subsume
  // la regla "await_documents primero" y el orden fijo de capacidades del backend
  // (Completitud → Calidad → Enriquecimiento → Análisis → Aprobación → Salida),
  // así que ni el menú «+» ni un arrastre pueden producir una receta inválida.
  let prevRank = Number.NEGATIVE_INFINITY;
  let outOfOrder = false;
  for (const s of orderedStages) {
    if (s.rank <= prevRank) outOfOrder = true;
    prevRank = s.rank;
  }
  if (outOfOrder) {
    msgs.push({
      level: "error",
      msg: "Las capacidades deben seguir su orden canónico: Completitud → Control de calidad → Enriquecimiento → Análisis → Aprobación → Salida.",
    });
  }
  if (!msgs.length) {
    msgs.push({
      level: "ok",
      msg: "Pipeline válido · frontera de scope respetada.",
    });
  }
  return msgs;
}

/** Edge path generator (bezier | step). */
export function edgePath(
  e: { x1: number; y1: number; x2: number; y2: number },
  style: "bezier" | "step"
): string {
  if (style === "step") {
    const mid = (e.y1 + e.y2) / 2;
    if (Math.abs(e.x1 - e.x2) < 1) return `M${e.x1} ${e.y1} L${e.x2} ${e.y2}`;
    return `M${e.x1} ${e.y1} V${mid} H${e.x2} V${e.y2}`;
  }
  const k = Math.max(22, Math.abs(e.y2 - e.y1) * 0.5);
  return `M${e.x1} ${e.y1} C${e.x1} ${e.y1 + k} ${e.x2} ${e.y2 - k} ${e.x2} ${e.y2}`;
}
