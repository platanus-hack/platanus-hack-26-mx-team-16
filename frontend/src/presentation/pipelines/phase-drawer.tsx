"use client";

import { useRef } from "react";

import type {
  PhaseCatalogEntry,
  PipelinePhase,
} from "@/src/application/hooks/queries/pipelines";
import { useAutoHideScrollbar } from "@/src/application/hooks/use-auto-hide-scrollbar";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/src/presentation/components/ui/sheet";
import { PhaseConfigForm } from "@/src/presentation/pipelines/phase-config-form";
import { phaseLabel } from "@/src/presentation/pipelines/pipeline-stages";

interface DoctypeOption {
  slug: string;
  name: string;
}

interface DestinationOption {
  uuid: string;
  name: string;
}

interface PhaseDrawerProps {
  /** Fase seleccionada; `null` cierra el drawer (controla `open` del Sheet). */
  phase: PipelinePhase | null;
  /** Entrada del catálogo para `phase.kind` (de dónde sale el `configSchema`). */
  entry: PhaseCatalogEntry | undefined;
  doctypes: DoctypeOption[];
  destinations: DestinationOption[];
  /** Error de validación (dry-run / local) atribuido a esta fase. */
  error?: string;
  readOnly?: boolean;
  onConfigChange: (config: Record<string, unknown>) => void;
  /** Lo invoca el Sheet al cerrarse (backdrop / Escape / botón ✕). */
  onOpenChange: (open: boolean) => void;
}

/**
 * Drawer de configuración por fase: hoja lateral derecha a **todo el alto de la
 * pantalla** (Sheet de Base UI, mismo patrón que `HelpSidebar`), con backdrop y
 * **scroll propio e independiente** del contenido del tab «Fases». Así, al abrir
 * una fase que está al final del lienzo, su configuración siempre se ve y se
 * desplaza por sí sola (el header queda fijo, solo el cuerpo hace scroll).
 *
 * El cuerpo muestra el formulario de config de la fase (`PhaseConfigForm`,
 * dirigido por el `configSchema` del catálogo). En solo lectura, un
 * `<fieldset disabled>` desactiva todos los controles.
 */
export function PhaseDrawer({
  phase,
  entry,
  doctypes,
  destinations,
  error,
  readOnly = false,
  onConfigChange,
  onOpenChange,
}: PhaseDrawerProps) {
  // Autohide del scrollbar del cuerpo (aparece solo al hacer scroll), igual que
  // las demás superficies desplazables del editor.
  const bodyRef = useRef<HTMLDivElement>(null);
  useAutoHideScrollbar(bodyRef);

  return (
    <Sheet open={phase !== null} onOpenChange={onOpenChange}>
      {/* Hoja a todo el alto (el Sheet ya es `fixed inset-y-0 right-0 h-full`).
          `gap-0 p-0` para que header y cuerpo manejen su propio espaciado y el
          cuerpo sea el único con scroll. Ancho cómodo y responsive. */}
      <SheetContent
        side="right"
        className="!w-full gap-0 p-0 sm:!max-w-xl lg:!max-w-2xl"
      >
        {phase && (
          <>
            <SheetHeader className="shrink-0 gap-0.5 border-b px-5 py-3.5 pr-12">
              <SheetTitle className="truncate font-semibold text-sm leading-tight">
                {phaseLabel(phase.kind)}
              </SheetTitle>
              <SheetDescription className="truncate font-mono text-muted-foreground text-xs leading-tight">
                {phase.kind}
              </SheetDescription>
            </SheetHeader>

            {/* Único elemento con scroll: independiente del scroll del tab. */}
            <div
              ref={bodyRef}
              className="scrollbar-subtle min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5"
            >
              {error && (
                <div
                  role="alert"
                  className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-destructive text-xs"
                >
                  {error}
                </div>
              )}
              {/* fieldset[disabled] desactiva todos los controles nativos anidados
                  (inputs, selects/switches de Base UI son <button>) en solo lectura. */}
              <fieldset
                disabled={readOnly}
                className="m-0 min-w-0 space-y-5 border-0 p-0"
              >
                <PhaseConfigForm
                  entry={entry}
                  config={phase.config}
                  doctypes={doctypes}
                  destinations={destinations}
                  readOnly={readOnly}
                  onChange={onConfigChange}
                />
              </fieldset>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
