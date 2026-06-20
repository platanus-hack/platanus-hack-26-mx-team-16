"use client";

import { Rocket, RotateCcw } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDocumentTypesQuery } from "@/src/application/hooks/queries/document-types";
import {
  asPipelineValidationError,
  type PhaseCatalogEntry,
  usePhaseCatalogQuery,
  usePublishVersionMutation,
  useValidateRecipeMutation,
  useWorkflowPipelineQuery,
  useWorkflowPipelineVersionQuery,
} from "@/src/application/hooks/queries/pipelines";
import { useWebhookDestinationsQuery } from "@/src/application/hooks/queries/webhook-destinations";
import { useAutoHideScrollbar } from "@/src/application/hooks/use-auto-hide-scrollbar";
import { usePipelineEditorStore } from "@/src/application/stores/pipeline-editor-store";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { ExecutionsPanel } from "@/src/presentation/pipelines/executions/executions-panel";
import { PhaseDrawer } from "@/src/presentation/pipelines/phase-drawer";
import { computePipelineDiff } from "@/src/presentation/pipelines/pipeline-diff";
import { validateRecipeStructure } from "@/src/presentation/pipelines/pipeline-validation";
import { PublishDiffDialog } from "@/src/presentation/pipelines/publish-diff-dialog";
import {
  buildDraft,
  buildSpine,
} from "@/src/presentation/pipelines/spine/adapter";
import { SpineCanvas } from "@/src/presentation/pipelines/spine/spine-canvas";
import type { PipelineState } from "@/src/presentation/pipelines/spine/types";
import { VersionHistory } from "@/src/presentation/pipelines/version-history";

interface PipelineEditorProps {
  /** Workflow propietario del pipeline (ADR 0002: relación 1:1). */
  workflowId: string;
  /**
   * Permite editar/publicar. Lo decide la página vía el gate "manage" del
   * workflow; el backend re-valida con require_workflow_action("manage").
   * Por defecto solo lectura.
   */
  canManage?: boolean;
}

// Referencias estables para los defaults de query (evitan re-render loops).
type DoctypeItem = NonNullable<
  ReturnType<typeof useDocumentTypesQuery>["data"]
>[number];
const EMPTY_CATALOG: PhaseCatalogEntry[] = [];
const EMPTY_DOCTYPES: DoctypeItem[] = [];

// Tabs navegables vía `?tab=`: la URL es la única fuente de verdad del tab
// activo, así cada uno es enlazable/recargable (mismo patrón que cases).
const PIPELINE_TABS = ["phases", "versions", "executions"] as const;
type PipelineTab = (typeof PIPELINE_TABS)[number];
const DEFAULT_PIPELINE_TAB: PipelineTab = "phases";

export function PipelineEditor({
  workflowId,
  canManage = false,
}: PipelineEditorProps) {
  // El gate autoritativo vive en el backend (require_workflow_action("manage"));
  // esto es solo UX. La página decide `canManage` a partir del permiso del
  // workflow; sin él, el editor es de solo lectura.
  const readOnly = !canManage;

  // Tab activo derivado de la URL (`?tab=`). `router.replace` actualiza la URL
  // sin empujar al historial; el render se dispara por `useSearchParams`.
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: PipelineTab = (PIPELINE_TABS as readonly string[]).includes(
    tabParam ?? ""
  )
    ? (tabParam as PipelineTab)
    : DEFAULT_PIPELINE_TAB;
  const handleTabChange = useCallback(
    (value: string) => {
      router.replace(`/workflows/${workflowId}/pipeline?tab=${value}`, {
        scroll: false,
      });
    },
    [router, workflowId]
  );

  const { data: pipeline, isLoading: pipelineLoading } =
    useWorkflowPipelineQuery(workflowId);

  // Defaults estables (módulo): `= []` inline crea un array nuevo cada render
  // mientras la query carga ⇒ el effect de validación (dep: catalog) re-corría
  // sin fin llamando setState con objetos frescos (Maximum update depth).
  const { data: catalogData } = usePhaseCatalogQuery();
  const { data: doctypesData } = useDocumentTypesQuery();
  const catalog = catalogData ?? EMPTY_CATALOG;
  const doctypes = doctypesData ?? EMPTY_DOCTYPES;
  const { data: activeVersion, isLoading: versionLoading } =
    useWorkflowPipelineVersionQuery(
      workflowId,
      pipeline?.currentVersion ?? null
    );
  const isLoading = pipelineLoading || versionLoading;

  const store = usePipelineEditorStore();
  const { phases, dirty, loadNonce, updatePhaseConfig } = store;

  // Destinos webhook del workflow (selector de `deliver.channels` en el drawer).
  const { data: destinationsData } = useWebhookDestinationsQuery(workflowId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Autohide del scrollbar de la superficie (aparece solo al hacer scroll).
  const scrollSurfaceRef = useRef<HTMLDivElement>(null);
  useAutoHideScrollbar(scrollSurfaceRef);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  // Errores de validación inline por phase.id (del dry-run o validación local).
  const [phaseErrors, setPhaseErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  const validateMutation = useValidateRecipeMutation(workflowId);
  const publishMutation = usePublishVersionMutation(workflowId);

  // Cargar el draft desde la versión activa cuando llega (o cambia el pipeline).
  // La identidad del draft en el store es el workflowId (ADR 0002: 1:1).
  const loadedVersionRef = useRef<number | null>(null);
  useEffect(() => {
    if (!activeVersion) return;
    const firstLoad = store.pipelineId !== workflowId;
    const versionChanged = loadedVersionRef.current !== activeVersion.version;
    if (firstLoad || (versionChanged && !dirty)) {
      store.load(workflowId, activeVersion);
      loadedVersionRef.current = activeVersion.version;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeVersion, workflowId]);

  const doctypeOptions = useMemo(
    () =>
      doctypes
        .filter((d) => d.slug)
        .map((d) => ({ slug: d.slug as string, name: d.name })),
    [doctypes]
  );

  const destinationOptions = useMemo(
    () => (destinationsData ?? []).map((d) => ({ uuid: d.uuid, name: d.name })),
    [destinationsData]
  );

  // Validación continua (debounced) vía dry-run. También valida localmente el
  // orden de scope para feedback inmediato.
  useEffect(() => {
    const localStructural = validateRecipeStructure(phases, catalog);
    const localErrors: Record<string, string> = {};
    for (const issue of localStructural)
      localErrors[issue.phaseId] = issue.message;

    if (!phases.length || !catalog.length) {
      setPhaseErrors(localErrors);
      setGlobalError(null);
      return;
    }

    const handle = setTimeout(() => {
      validateMutation.mutate(
        { phases },
        {
          onSuccess: () => {
            setPhaseErrors(localErrors);
            setGlobalError(
              Object.keys(localErrors).length
                ? "Hay problemas estructurales en la receta."
                : null
            );
          },
          onError: (err) => {
            const ve = asPipelineValidationError(err);
            // Intenta atribuir el error a una fase concreta por su id en el detalle.
            if (ve) {
              const guilty = phases.find((p) =>
                ve.detail.includes(`'${p.id}'`)
              );
              if (guilty) localErrors[guilty.id] = ve.detail;
              setGlobalError(guilty ? null : ve.detail);
            } else {
              setGlobalError("No se pudo validar la receta.");
            }
            setPhaseErrors(localErrors);
          },
        }
      );
    }, 500);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phases, catalog]);

  // Modelo del editor visual (spine) derivado de la receta real.
  const spine = useMemo(() => buildSpine(phases), [phases]);

  // El spine emite la estructura nueva (orden/opcionales/alta-baja de etapas);
  // la traducimos a la receta del store. Lee el store con getState() para no
  // depender de un closure viejo si llegan varios cambios seguidos.
  const handleSpineChange = useCallback(
    (state: PipelineState) => {
      const s = usePipelineEditorStore.getState();
      const next = buildDraft(state, s.phases, catalog);
      const changed = JSON.stringify(next.phases) !== JSON.stringify(s.phases);
      if (changed) s.setDraft(next);
    },
    [catalog]
  );

  const diff = useMemo(() => {
    if (!activeVersion) return null;
    return computePipelineDiff({ phases: activeVersion.phases }, { phases });
  }, [activeVersion, phases]);

  const hasErrors = Object.keys(phaseErrors).length > 0 || Boolean(globalError);

  function openPublish() {
    setPublishError(null);
    setPublishOpen(true);
  }

  function confirmPublish() {
    setPublishError(null);
    publishMutation.mutate(
      {
        phases,
        outputSchema: store.outputSchema,
      },
      {
        onSuccess: () => {
          setPublishOpen(false);
          store.reset();
        },
        onError: (err) => {
          const ve = asPipelineValidationError(err);
          setPublishError(
            ve ? `${ve.error}: ${ve.detail}` : "No se pudo publicar la versión."
          );
        },
      }
    );
  }

  const selectedPhase = phases.find((p) => p.id === selectedId) ?? null;
  const selectedEntry = selectedPhase
    ? catalog.find((e) => e.kind === selectedPhase.kind)
    : undefined;

  if (isLoading || !pipeline) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">
          Cargando receta…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="flex min-h-0 flex-1 flex-col gap-3"
      >
        {/* Barra fija: tabs a la izquierda, acciones a la derecha. Solo el
            contenido de abajo hace scroll. */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TabsList>
              <TabsTrigger value="phases">Fases</TabsTrigger>
              <TabsTrigger value="versions">Versiones</TabsTrigger>
              <TabsTrigger value="executions">Ejecuciones</TabsTrigger>
            </TabsList>
            {dirty && (
              <Badge className="text-[10px]">cambios sin publicar</Badge>
            )}
          </div>
          {!readOnly && (
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={!dirty || publishMutation.isPending}
                onClick={() =>
                  activeVersion && store.load(workflowId, activeVersion)
                }
              >
                <RotateCcw className="size-4" /> Descartar
              </Button>
              <ActionButton
                type="button"
                icon={<Rocket className="size-4" />}
                disabled={!dirty || hasErrors}
                onClick={openPublish}
              >
                Publicar
              </ActionButton>
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <TabsContent
            value="phases"
            className="mt-0 flex h-full min-h-0 flex-col gap-3"
          >
            {globalError && (
              <div
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
              >
                {globalError}
              </div>
            )}

            {/* El lienzo es la ÚNICA superficie con scroll del tab. El drawer de
                config es una hoja lateral aparte (Sheet a todo el alto, montada
                fuera de este contenedor) con su propio scroll independiente, así
                la config de una fase al final del lienzo siempre se ve. El spine
                se re-monta (key) al cargar/descartar. */}
            <div
              ref={scrollSurfaceRef}
              className="scrollbar-subtle min-h-0 flex-1 overflow-auto rounded-xl border bg-card"
            >
              <SpineCanvas
                key={`${workflowId}:${loadNonce}`}
                stages={spine.stages}
                initialState={spine.state}
                addable={spine.addable}
                appearance={{ background: "cuadricula" }}
                readOnly={readOnly}
                selectedId={selectedId}
                onChange={handleSpineChange}
                onSelectPhase={setSelectedId}
              />
            </div>
          </TabsContent>

          <TabsContent value="versions" className="mt-0">
            <VersionHistory
              workflowId={workflowId}
              currentVersion={pipeline.currentVersion}
            />
          </TabsContent>

          <TabsContent value="executions" className="mt-0 h-full min-h-0">
            <ExecutionsPanel workflowId={workflowId} />
          </TabsContent>
        </div>
      </Tabs>

      {/* Drawer de configuración por fase: hoja lateral a todo el alto, con
          scroll propio. Montado fuera del scroll del tab; se abre al seleccionar
          una fase (selectedId) y se cierra por backdrop/Escape/✕. */}
      <PhaseDrawer
        phase={selectedPhase}
        entry={selectedEntry}
        doctypes={doctypeOptions}
        destinations={destinationOptions}
        error={selectedPhase ? phaseErrors[selectedPhase.id] : undefined}
        readOnly={readOnly}
        onConfigChange={(config) => {
          if (selectedPhase) updatePhaseConfig(selectedPhase.id, config);
        }}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
      />

      {diff && (
        <PublishDiffDialog
          open={publishOpen}
          onOpenChange={setPublishOpen}
          diff={diff}
          currentVersion={pipeline.currentVersion}
          publishing={publishMutation.isPending}
          error={publishError}
          onConfirm={confirmPublish}
        />
      )}
    </div>
  );
}
