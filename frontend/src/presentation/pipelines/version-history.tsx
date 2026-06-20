"use client";

import { ArrowRight, GitCompare, Layers } from "lucide-react";
import { useMemo, useState } from "react";

import {
  type PipelineVersionSummary,
  useWorkflowPipelineVersionQuery,
  useWorkflowPipelineVersionsQuery,
} from "@/src/application/hooks/queries/pipelines";
import { cn } from "@/src/application/lib/utils";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  computePipelineDiff,
  type PhaseChangeKind,
} from "@/src/presentation/pipelines/pipeline-diff";

interface VersionHistoryProps {
  workflowId: string;
  currentVersion: number;
}

// Cada tipo de cambio se pinta con un color semántico del sistema: alta = teal,
// eliminación = destructivo, movimiento = ámbar, edición = primario.
const KIND_META: Record<PhaseChangeKind, { label: string; chip: string }> = {
  added: {
    label: "añadida",
    chip: "bg-success/10 text-success-deep ring-success/25",
  },
  removed: {
    label: "eliminada",
    chip: "bg-destructive/10 text-destructive-deep ring-destructive/25",
  },
  moved: {
    label: "movida",
    chip: "bg-warning/15 text-warning-deep ring-warning/30",
  },
  modified: {
    label: "editada",
    chip: "bg-primary/10 text-primary ring-primary/25",
  },
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/** Ranura de la barra de comparación: hueca (placeholder) o con la versión elegida. */
function CompareSlot({
  value,
  placeholder,
}: {
  value: number | null;
  placeholder: string;
}) {
  if (value == null) {
    return (
      <span className="rounded-md border border-dashed border-border px-2 py-0.5 font-mono text-xs text-muted-foreground">
        {placeholder}
      </span>
    );
  }
  return (
    <span className="rounded-md bg-primary/10 px-2 py-0.5 font-mono text-xs font-medium text-primary ring-1 ring-inset ring-primary/25">
      v{value}
    </span>
  );
}

function changeLines(change: {
  change: PhaseChangeKind;
  fromIndex?: number;
  toIndex?: number;
  details?: string[];
}): string[] {
  switch (change.change) {
    case "moved":
      return [
        `posición ${(change.fromIndex ?? 0) + 1} → ${(change.toIndex ?? 0) + 1}`,
      ];
    case "modified":
      return change.details ?? [];
    default:
      return [];
  }
}

export function VersionHistory({
  workflowId,
  currentVersion,
}: VersionHistoryProps) {
  const { data: versions, isLoading } =
    useWorkflowPipelineVersionsQuery(workflowId);
  // Diff de dos versiones: A (base) vs B (objetivo).
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);

  const versionA = useWorkflowPipelineVersionQuery(workflowId, a, {
    enabled: a != null,
  });
  const versionB = useWorkflowPipelineVersionQuery(workflowId, b, {
    enabled: b != null,
  });

  // Más reciente arriba: el riel se lee como un changelog (la activa encabeza).
  const ordered = useMemo(
    () => [...(versions ?? [])].sort((x, y) => y.version - x.version),
    [versions]
  );

  const diff = useMemo(() => {
    if (!versionA.data || !versionB.data) return null;
    return computePipelineDiff(
      { phases: versionA.data.phases },
      { phases: versionB.data.phases }
    );
  }, [versionA.data, versionB.data]);

  function pick(version: number) {
    // Primer click = A (base), segundo = B (objetivo), tercero reinicia.
    if (a == null) setA(version);
    else if (b == null && version !== a) setB(version);
    else {
      setA(version);
      setB(null);
    }
  }

  function reset() {
    setA(null);
    setB(null);
  }

  const guidance =
    a == null
      ? "Elige la versión base en la lista."
      : b == null
        ? "Ahora elige la versión a comparar."
        : `Comparando v${a} (base) con v${b} (objetivo).`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Layers className="size-4 text-primary" />
          Versiones
        </CardTitle>
        <CardDescription>
          Cada publicación crea una versión inmutable. Elige dos para comparar
          sus recetas y políticas.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Barra de comparación: dos ranuras base → objetivo con guía viva. */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 rounded-lg border bg-muted/30 px-3 py-2">
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Comparar
          </span>
          <CompareSlot value={a} placeholder="base" />
          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
          <CompareSlot value={b} placeholder="objetivo" />
          {(a != null || b != null) && (
            <button
              type="button"
              onClick={reset}
              className="ml-auto rounded text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Limpiar
            </button>
          )}
          <p className="basis-full text-xs text-muted-foreground">{guidance}</p>
        </div>

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando versiones…</p>
        ) : !ordered.length ? (
          <div className="rounded-lg border border-dashed px-4 py-8 text-center">
            <p className="text-sm font-medium">Aún no hay versiones</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Publica la receta desde la pestaña Fases para crear la v1.
            </p>
          </div>
        ) : (
          <ul className="rounded-md ring-1 ring-inset ring-foreground/10">
            {ordered.map((v: PipelineVersionSummary, i) => {
              const role = v.version === a ? "A" : v.version === b ? "B" : null;
              const isActive = v.version === currentVersion;
              const isFirst = i === 0;
              const isLast = i === ordered.length - 1;
              return (
                <li
                  key={v.version}
                  className={cn(
                    "relative flex items-stretch",
                    !isFirst && "border-t border-border"
                  )}
                >
                  {/* Riel del changelog: conector vertical + nodo de la versión. */}
                  <div className="relative flex w-9 shrink-0 items-center justify-center">
                    {!isFirst && (
                      <span className="absolute left-1/2 top-0 h-1/2 w-px -translate-x-1/2 bg-border" />
                    )}
                    {!isLast && (
                      <span className="absolute bottom-0 left-1/2 h-1/2 w-px -translate-x-1/2 bg-border" />
                    )}
                    <span
                      aria-hidden
                      className={cn(
                        "relative z-10 size-3 rounded-full border-2 border-card transition-colors",
                        isActive
                          ? "bg-primary"
                          : role
                            ? "border-primary bg-primary/25"
                            : "bg-muted-foreground/40"
                      )}
                    />
                  </div>

                  <button
                    type="button"
                    aria-pressed={role != null}
                    onClick={() => pick(v.version)}
                    className={cn(
                      "flex flex-1 items-center justify-between gap-3 rounded-r-md px-3 py-2.5 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                      role && "bg-primary/[0.06]"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium tabular-nums">
                        v{v.version}
                      </span>
                      {isActive && (
                        <Badge variant="secondary" className="text-[10px]">
                          activa
                        </Badge>
                      )}
                      {role && (
                        <Badge className="text-[10px]">
                          {role === "A" ? "base" : "objetivo"}
                        </Badge>
                      )}
                    </span>
                    <span className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="tabular-nums">{v.phaseCount} fases</span>
                      <span className="font-mono tabular-nums">
                        {formatDate(v.createdAt)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {a != null && b != null && (
          <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
            <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <GitCompare className="size-3.5" />
              Cambios de <span className="font-mono text-foreground">v{a}</span>
              <ArrowRight className="size-3" />
              <span className="font-mono text-foreground">v{b}</span>
            </p>
            {!diff ? (
              <p className="text-sm text-muted-foreground">Cargando diff…</p>
            ) : diff.empty ? (
              <p className="text-sm text-muted-foreground">
                Sin diferencias estructurales.
              </p>
            ) : (
              <div className="space-y-1.5">
                {diff.phases.map((c) => {
                  const meta = KIND_META[c.change];
                  const lines = changeLines(c);
                  return (
                    <div
                      key={`${c.id}-${c.change}`}
                      className="flex items-start gap-2"
                    >
                      <span
                        className={cn(
                          "mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset",
                          meta.chip
                        )}
                      >
                        {meta.label}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm">
                          <span className="font-mono">{c.id}</span>
                          <span className="text-muted-foreground">
                            {" "}
                            · {c.kind}
                          </span>
                        </p>
                        {lines.map((line) => (
                          <p
                            key={line}
                            className="font-mono text-xs text-muted-foreground"
                          >
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
