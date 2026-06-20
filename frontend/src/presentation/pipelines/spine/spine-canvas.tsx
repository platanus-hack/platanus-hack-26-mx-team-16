"use client";
// spine-canvas.tsx — lienzo del editor de pipeline (spine vertical) adaptado a
// Doxiq. Es el `pipeline-editor.tsx` del paquete SIN su toolbar ni su inspector:
//   · la barra (tabs + Publicar/Descartar) vive en el host;
//   · la edición de config la hace PhaseDrawer (vía onSelectPhase).
// Maneja ESTRUCTURA (orden, opcionales, alta/baja de etapas, scope frontier) y
// emite onChange(PipelineState); el host lo traduce a la receta del store.
import * as React from "react";
import { useIsMobile } from "@/src/application/hooks/use-mobile";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/src/presentation/components/ui/alert-dialog";

import "./pipeline-editor.css";
import "./spine-theme.css";

import { getAccent } from "./accents";
import { PipeIcon } from "./icons";
import { type Block, computeLayout } from "./layout";
import {
  CollapsedGroup,
  GroupBox,
  InnerNode,
  type NodeCommon,
  PipeEdges,
  ScopeChip,
  SoloNode,
} from "./nodes";
import {
  type Appearance,
  DEFAULT_APPEARANCE,
  type PipelineState,
  type Selection,
  type Stage,
} from "./types";
import { usePipeline } from "./use-pipeline";

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export interface SpineCanvasProps {
  stages: Stage[];
  initialState: PipelineState;
  addable: string[];
  appearance?: Partial<Appearance>;
  readOnly?: boolean;
  /** Id de la fase real con el panel de config abierto (resalta su nodo). */
  selectedId?: string | null;
  onChange: (state: PipelineState) => void;
  /** Abre/cierra el panel de config de una fase (id real, o null). */
  onSelectPhase: (realId: string | null) => void;
}

export function SpineCanvas({
  stages,
  initialState,
  addable,
  appearance,
  readOnly = false,
  selectedId = null,
  onChange,
  onSelectPhase,
}: SpineCanvasProps) {
  const ui: Appearance = { ...DEFAULT_APPEARANCE, ...appearance };

  const isMobile = useIsMobile();
  const density = ui.density;

  // Ancho disponible de la columna del canvas (sin scrollbar). Lo medimos para el
  // modo FLUIDO en móvil: el "mundo" toma este ancho y las tarjetas lo LLENAN a
  // escala 1 (texto a tamaño normal, con wrap) en vez de encoger todo el lienzo.
  // En desktop las dims son naturales; si la columna se estrecha (drawer abierto)
  // se aplica escalado-para-encajar (`fitScale`). `transform` no afecta
  // `offsetHeight`, así que la medición de alturas sigue siendo válida.
  const rootRef = React.useRef<HTMLDivElement>(null);
  const [availW, setAvailW] = React.useState(0);
  React.useLayoutEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const update = () => setAvailW(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Móvil → mundo fluido (cards a ancho completo). Desktop → dims naturales.
  const fluid = isMobile && availW > 0;
  const fitWidth = fluid ? availW - 2 : undefined;

  const p = usePipeline({ stages, initialState, addable, onChange });
  const { state, orderedStages, sel, flash, hasCaseScope } = p;

  // «Quitar scope de caso» SIEMPRE confirma (puede borrar config de enrich/
  // analyze/policies). «Agregar» no necesita confirmación.
  const [confirmRemoveScope, setConfirmRemoveScope] = React.useState(false);

  const handleSelect = React.useCallback(
    (s: NonNullable<Selection>) => {
      p.setSel(s);
      onSelectPhase(s.id ?? null);
    },
    [p, onSelectPhase]
  );

  // Alturas reales medidas del DOM (cards a `height: auto`). El motor las usa
  // para posicionar; el useLayoutEffect de abajo re-mide tras cada render y
  // converge en un pase (la altura natural depende solo del ancho fijo + contenido).
  const [heights, setHeights] = React.useState<Record<string, number>>({});

  const layout = React.useMemo(
    () =>
      computeLayout(orderedStages, {
        collapsed: state.collapsed,
        density,
        heights,
        fitWidth,
      }),
    [orderedStages, state.collapsed, density, heights, fitWidth]
  );
  const accentOf = React.useCallback(
    (s: Stage) => getAccent(s.accent, ui.palette),
    [ui.palette]
  );

  const worldRef = React.useRef<HTMLDivElement>(null);

  React.useLayoutEffect(() => {
    const world = worldRef.current;
    if (!world) return;
    const measured: Record<string, number> = {};
    for (const b of layout.blocks) {
      if (b.isGroup && !b.collapsed && b.inner) {
        for (const n of b.inner.nodes) {
          const el = world.querySelector<HTMLElement>(
            `[data-pe-measure="${n.id}"]`
          );
          if (el) measured[n.id] = el.offsetHeight;
        }
      } else {
        const el = world.querySelector<HTMLElement>(
          `[data-pe-measure="${b.id}"]`
        );
        if (el) measured[b.id] = el.offsetHeight;
      }
    }
    let changed = Object.keys(measured).length !== Object.keys(heights).length;
    if (!changed) {
      for (const k in measured) {
        if (Math.abs(measured[k] - (heights[k] ?? 0)) > 0.5) {
          changed = true;
          break;
        }
      }
    }
    if (changed) setHeights(measured);
  }, [layout, heights]);

  const [addMenu, setAddMenu] = React.useState<{
    at: number;
    wx: number;
    wy: number;
  } | null>(null);

  const onCanvasClick = (e: React.MouseEvent) => {
    if (
      !(e.target as HTMLElement).closest(
        ".pe-card,.pe-group,.pe-inner,.pe-addbtn,.pe-addmenu"
      )
    ) {
      p.setSel(null);
      onSelectPhase(null);
      setAddMenu(null);
    }
  };

  const blockEls = layout.blocks.map((b) => {
    const accent = accentOf(b.stage);
    const isSel = !!sel && sel.stageId === b.id && !sel.kind;
    const common = {
      accent,
      ui,
      selected: isSel,
      onSelect: handleSelect,
      onToggleCollapse: p.toggleCollapse,
      onRemove: readOnly ? undefined : p.removeStage,
    };
    if (b.isGroup && !b.collapsed && b.inner) {
      return (
        <div
          key={b.id}
          style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
        >
          <GroupBox block={b} {...common} />
          {b.inner.nodes.map((n) => {
            const off =
              !!n.phase.optional && state.optional[n.phase.kind] === false;
            const nodeSel = !!n.phase.realId && n.phase.realId === selectedId;
            return (
              <InnerNode
                key={n.phase.kind + (n.phase.realId ?? "")}
                node={{ ...n, stageId: b.id }}
                accent={accent}
                ui={ui}
                selected={nodeSel}
                disabled={off}
                onSelect={handleSelect}
                onToggleOptional={readOnly ? () => {} : p.toggleOptional}
              />
            );
          })}
        </div>
      );
    }
    const Comp = (b.isGroup ? CollapsedGroup : SoloNode) as React.FC<
      NodeCommon & { block: Block }
    >;
    const soloSel =
      !b.isGroup &&
      !!b.stage.phases[0]?.realId &&
      b.stage.phases[0].realId === selectedId;
    return (
      <div
        key={b.id}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        <Comp block={b} {...common} selected={isSel || soloSel} />
      </div>
    );
  });

  // Un hueco solo admite capacidades cuyo rank canónico cabe entre sus vecinos.
  // Donde nada cabe —p. ej. la frontera documento→caso, sin rangos intermedios—
  // el «+» sería un callejón sin salida (y se encimaba con la etiqueta de la
  // frontera): no lo dibujamos.
  const fitsAt = (atIdx: number) =>
    p.missing.some((id) => {
      const r = p.byId[id]?.rank;
      if (r == null) return false;
      const prevRank =
        orderedStages[atIdx - 1]?.rank ?? Number.NEGATIVE_INFINITY;
      const nextRank = orderedStages[atIdx]?.rank ?? Number.POSITIVE_INFINITY;
      return r > prevRank && r < nextRank;
    });

  const addEls = readOnly
    ? null
    : layout.edges
        .filter((e) => fitsAt(e.idx + 1))
        .map((e) => (
          <button
            type="button"
            key={`add${e.idx}`}
            className="pe-addbtn"
            style={{ left: e.x1, top: (e.y1 + e.y2) / 2 }}
            title="Insertar etapa aquí"
            onMouseDown={(ev) => ev.stopPropagation()}
            onClick={(ev) => {
              ev.stopPropagation();
              setAddMenu(
                addMenu && addMenu.at === e.idx + 1
                  ? null
                  : { at: e.idx + 1, wx: e.x1, wy: (e.y1 + e.y2) / 2 }
              );
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        ));

  // El menú «+» de cada hueco solo ofrece capacidades cuyo rank canónico cabe
  // entre sus vecinos, así no se puede romper el orden fijo de capacidades
  // (Completitud → Control de calidad → Enriquecimiento → Análisis → Aprobación → Salida).
  const menuItems = addMenu
    ? p.missing.filter((id) => {
        const r = p.byId[id]?.rank;
        if (r == null) return false;
        const prevRank =
          orderedStages[addMenu.at - 1]?.rank ?? Number.NEGATIVE_INFINITY;
        const nextRank =
          orderedStages[addMenu.at]?.rank ?? Number.POSITIVE_INFINITY;
        return r > prevRank && r < nextRank;
      })
    : [];

  // Tarjeta-fantasma «Agregar scope de caso»: bajo el último bloque, centrada en
  // el eje del spine. Extiende el alto del mundo para que no se recorte.
  const lastBlock = layout.blocks[layout.blocks.length - 1];
  const showCaseGhost = !readOnly && !hasCaseScope && !!lastBlock;
  const ghostTop = lastBlock
    ? lastBlock.y + lastBlock.h + layout.D.blockGap
    : 56;
  const ghostH = 92;
  const worldH = showCaseGhost
    ? Math.max(layout.worldH, ghostTop + ghostH + 24)
    : layout.worldH;

  // Escalado-para-encajar SOLO en desktop: si la columna se estrecha (drawer
  // abierto) y el mundo natural no cabe, se reduce proporcionalmente y queda
  // centrado. En móvil el mundo ya es fluido (= ancho disponible), así que no se
  // escala → texto a tamaño normal.
  const FIT_GUTTER = 8;
  const fitScale =
    !fluid && availW > 0
      ? Math.min(1, (availW - FIT_GUTTER) / layout.worldW)
      : 1;

  // Sangría de las bandas de scope (etiquetas DOCUMENTO/CASO + pill «Quitar»):
  // alineadas a los bordes de la columna de tarjetas (ancho de grupo), dejando
  // libre el eje central del spine.
  const bandInset = layout.CX - layout.D.groupW / 2 - 40;
  const docBandTop = layout.blocks[0]
    ? Math.max(layout.blocks[0].y - 30, 14)
    : 14;

  return (
    <div className="pe-root" ref={rootRef}>
      <div className={`pe-vp bg-${ui.background}`} onClick={onCanvasClick}>
        <div
          className="pe-fit"
          style={{
            width: layout.worldW * fitScale,
            height: worldH * fitScale,
            margin: "0 auto",
          }}
        >
          <div
            ref={worldRef}
            className="pe-world"
            data-d={density}
            data-ns={ui.nodeStyle}
            style={{
              width: layout.worldW,
              height: worldH,
              transform: fitScale === 1 ? undefined : `scale(${fitScale})`,
              transformOrigin: "top left",
            }}
          >
            {layout.blocks[0] && (
              <div
                className="pe-frontier"
                style={{ top: docBandTop, left: 40, width: layout.worldW - 80 }}
              >
                <span className="pe-frontier-lbl" style={{ left: bandInset }}>
                  Documento
                </span>
              </div>
            )}

            {layout.frontierY != null && (
              <div
                className="pe-frontier"
                style={{
                  top: layout.frontierY,
                  left: 40,
                  width: layout.worldW - 80,
                }}
              >
                <span className="pe-frontier-lbl" style={{ left: bandInset }}>
                  Caso
                </span>
                {!readOnly && hasCaseScope && (
                  <button
                    type="button"
                    className="pe-frontier-remove"
                    style={{ right: bandInset }}
                    title="Quitar el scope de caso (vuelve a procesar por documento)"
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmRemoveScope(true);
                    }}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="12" r="9" />
                      <path d="M9 12h6" />
                    </svg>
                    Quitar caso
                  </button>
                )}
              </div>
            )}
            <PipeEdges layout={layout} ui={ui} />
            {blockEls}
            {addEls}

            {showCaseGhost && (
              <button
                type="button"
                className="pe-scope-add"
                style={{
                  left: layout.CX,
                  top: ghostTop,
                  width: Math.min(332, layout.D.soloW),
                }}
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => {
                  e.stopPropagation();
                  p.addCaseScope();
                }}
              >
                <span className="pe-scope-add-plus">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                  >
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                </span>
                <span className="pe-scope-add-text">
                  <span className="pe-scope-add-title">Agregar caso</span>
                  <span className="pe-scope-add-sub">
                    Acumula documentos en un expediente; el caso se cierra al
                    entregar.
                  </span>
                </span>
              </button>
            )}

            {addMenu && (
              <div
                className="pe-addmenu"
                style={{
                  left: clamp(addMenu.wx + 6, 6, layout.worldW - 230),
                  top: addMenu.wy + 6,
                }}
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="pe-addmenu-h">Insertar etapa</div>
                {menuItems.length ? (
                  menuItems.map((id) => {
                    const s = p.byId[id];
                    const a = accentOf(s);
                    return (
                      <button
                        type="button"
                        key={id}
                        className="pe-addmenu-i"
                        onClick={() => {
                          p.insertStage(id, addMenu.at);
                          setAddMenu(null);
                        }}
                      >
                        <span className="pe-ico sm" style={{ color: a.solid }}>
                          <PipeIcon name={s.icon} size={15} />
                        </span>
                        <span className="pe-addmenu-name">{s.name}</span>
                        <ScopeChip scope={s.scope} />
                      </button>
                    );
                  })
                ) : (
                  <div className="pe-addmenu-empty">
                    No hay capacidades que encajen aquí según el orden.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {flash && <div className="pe-flash">{flash}</div>}
      </div>

      <AlertDialog
        open={confirmRemoveScope}
        onOpenChange={setConfirmRemoveScope}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Quitar el scope de caso?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminarán todas las etapas de caso (Completitud, Control de
              calidad, Enriquecimiento, Análisis, Aprobación y Salida) junto con
              su configuración. El workflow pasará a procesarse por documento
              (straight-through): cada archivo se cierra al finalizar. Podrás
              volver a agregar el scope de caso, pero la configuración eliminada
              no se recupera.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                p.removeCaseScope();
                setConfirmRemoveScope(false);
              }}
            >
              Quitar caso
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default SpineCanvas;
