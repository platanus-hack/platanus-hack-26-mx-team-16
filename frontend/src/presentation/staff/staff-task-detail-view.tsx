"use client";

import {
  ArrowLeft,
  Check,
  FileText,
  Inbox,
  Lock,
  LockOpen,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  backendErrorCode,
  backendErrorMessage,
  useClaimStaffTaskMutation,
  useResolveStaffTaskMutation,
  useStaffCaseQuery,
  useStaffTasksQuery,
  type StaffCaseDocument,
  type StaffTask,
} from "@/src/application/hooks/queries/staff-tasks";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { CaseStatus, type CaseEvent } from "@/src/domain/entities/case";
import { CaseTimeline } from "@/src/presentation/workflows/cases/case-timeline";
import { caseStatusConfig } from "@/src/presentation/workflows/cases/case-status-config";
import { getStaffActor, rememberStaffActor } from "./staff-actor";
import { kindBadge, shortActor, stageBadge } from "./staff-queue-view";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Label } from "@/src/presentation/components/ui/label";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import { Textarea } from "@/src/presentation/components/ui/textarea";

/* ───────────────────────── helpers de campo ───────────────────────── */

/** Tier de confianza — espejo de `confidenceTier` del PDFViewer. */
function confidenceClass(confidence: number | null): string {
  if (confidence == null) return "bg-muted-foreground";
  if (confidence >= 0.9) return "bg-success";
  if (confidence >= 0.7) return "bg-warning";
  return "bg-destructive";
}

/** `needs_clarification` admite lista de strings/objetos o dict por campo. */
function isFlagged(
  needsClarification: StaffCaseDocument["needsClarification"],
  fieldPath: string
): boolean {
  if (!needsClarification) return false;
  if (Array.isArray(needsClarification)) {
    return needsClarification.some((item) => {
      if (typeof item === "string") return item === fieldPath;
      if (item && typeof item === "object") {
        const o = item as Record<string, unknown>;
        return o.fieldPath === fieldPath || o.field === fieldPath;
      }
      return false;
    });
  }
  return fieldPath in needsClarification;
}

function verificationLabel(level: number | undefined): string {
  if (level === 0) return "Verificado · externo";
  if (level === 1) return "Verificado · L1";
  if (level === 2) return "Verificado · L2";
  return "Verificado";
}

/* ─────────────────────── documento read-only ─────────────────────── */

/**
 * Tabla de campos read-only del bench staff. El agregado `/staff/v1/cases`
 * NO trae URL de archivo (los 5 endpoints del ADR no exponen descarga), así
 * que aquí no se monta PDFViewer: solo dato extraído + confianza + estado.
 * Orden por confianza ascendente (lo dudoso primero), como el bench tenant.
 */
function StaffDocumentCard({ document }: { document: StaffCaseDocument }) {
  const entries = useMemo(() => {
    const mapped = document.mappedExtraction ?? {};
    const confidenceOf = (key: string): number | null =>
      document.fieldConfidence?.[key] ??
      (mapped[key]?.bbox?.[0]?.confidence ?? null);
    return Object.entries(mapped)
      .map(([key, field]) => ({
        key,
        value: field?.value ?? null,
        confidence: confidenceOf(key),
      }))
      .sort((a, b) => (a.confidence ?? -1) - (b.confidence ?? -1));
  }, [document.mappedExtraction, document.fieldConfidence]);

  return (
    <div className="rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-3">
        <FileText className="size-4 text-muted-foreground" />
        <span className="truncate text-sm font-medium">
          {document.fileName ?? document.documentId.slice(0, 8)}
        </span>
        {document.status && (
          <Badge variant="secondary">{document.status}</Badge>
        )}
        {document.source && <Badge variant="outline">{document.source}</Badge>}
      </div>
      {entries.length === 0 ? (
        <p className="px-4 py-6 text-sm text-muted-foreground">
          Sin extracción mapeada para este documento.
        </p>
      ) : (
        <ul className="divide-y">
          {entries.map(({ key, value, confidence }) => {
            const verification = document.verification?.[key];
            const flagged = isFlagged(document.needsClarification, key);
            return (
              <li
                key={key}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-2.5 sm:grid-cols-[14rem_minmax(0,1fr)_auto]"
              >
                <span
                  className="truncate text-xs font-medium text-muted-foreground"
                  title={key}
                >
                  {key}
                </span>
                <span className="col-span-2 truncate font-mono text-[0.8125rem] sm:col-span-1">
                  {value == null || value === "" ? "—" : String(value)}
                </span>
                <span className="flex items-center justify-end gap-2">
                  {flagged && !verification && (
                    <Badge variant="warning">Por aclarar</Badge>
                  )}
                  {verification && (
                    <Badge variant="success">
                      {verificationLabel(verification.level)}
                    </Badge>
                  )}
                  <span className="flex items-center gap-1.5 text-xs tabular-nums text-muted-foreground">
                    <span
                      className={`size-1.5 rounded-full ${confidenceClass(confidence)}`}
                      aria-hidden
                    />
                    {confidence != null ? `${Math.round(confidence * 100)}%` : "—"}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ───────────────────────── resolución L1 ───────────────────────── */

function ResolveDialog({
  task,
  mode,
  onOpenChange,
}: {
  task: StaffTask;
  mode: "approve" | "reject";
  onOpenChange: (open: boolean) => void;
}) {
  const resolve = useResolveStaffTaskMutation();
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [openFields, setOpenFields] = useState<string[] | null>(null);
  const approving = mode === "approve";

  const submit = (force: boolean) => {
    setError(null);
    const trimmed = comment.trim();
    if (!approving && !trimmed) {
      setError("Para rechazar, escribe un comentario explicando el motivo.");
      return;
    }
    const resolution: Record<string, unknown> = { approved: approving };
    if (trimmed) resolution.comment = trimmed;
    if (force) resolution.force = true;
    resolve.mutate(
      { taskId: task.uuid, resolution },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => {
          const code = backendErrorCode(e);
          if (code === "human_task.open_flags") {
            const data = (e as { response?: { data?: unknown } }).response
              ?.data as
              | {
                  errors?: {
                    context?: { openFields?: string[]; open_fields?: string[] };
                  }[];
                }
              | undefined;
            const ctx = data?.errors?.[0]?.context;
            setOpenFields(ctx?.openFields ?? ctx?.open_fields ?? []);
            return;
          }
          setError(backendErrorMessage(e));
        },
      }
    );
  };

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-md p-6">
        <DialogHeader>
          <DialogTitle>
            {approving ? "Aprobar revisión L1" : "Rechazar caso"}
          </DialogTitle>
          <DialogDescription>
            {approving
              ? "El caso pasará al siguiente nivel de revisión o continuará su procesamiento."
              : "El caso quedará rechazado y no se generará ni entregará el resultado."}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor={`staff-comment-${task.uuid}`}>
              Comentario{approving ? " (opcional)" : ""}
            </Label>
            <Textarea
              id={`staff-comment-${task.uuid}`}
              autoFocus
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={
                approving
                  ? "Notas de la revisión para el historial…"
                  : "Motivo del rechazo…"
              }
            />
          </div>
          {openFields !== null && (
            <div className="space-y-2 rounded-md bg-warning/10 p-3">
              <p className="text-sm font-medium text-warning-deep">
                Hay campos flageados sin verificar:
              </p>
              <ul className="list-inside list-disc font-mono text-xs text-warning-deep">
                {openFields.length > 0 ? (
                  openFields.map((f) => <li key={f}>{f}</li>)
                ) : (
                  <li>campos pendientes de verificación</li>
                )}
              </ul>
              <p className="text-xs text-muted-foreground">
                Verifica los campos en el bench del tenant o fuerza la
                aprobación bajo tu responsabilidad.
              </p>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          {openFields !== null && approving ? (
            <ActionButton
              variant="destructive"
              icon={<Check />}
              loading={resolve.isPending}
              onClick={() => submit(true)}
            >
              Forzar aprobación
            </ActionButton>
          ) : (
            <ActionButton
              variant={approving ? "success" : "destructive"}
              icon={approving ? <Check /> : <X />}
              loading={resolve.isPending}
              onClick={() => submit(false)}
            >
              {approving ? "Aprobar" : "Rechazar"}
            </ActionButton>
          )}
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

/* ────────────────────────── veredicto QA ────────────────────────── */

/**
 * E6 §3 — resolución de una task QA (auditoría post-completado). El backend
 * espera `{ passed: bool, findings?: str }` (NO `{ approved }`); el veredicto
 * se registra como `qa.passed`/`qa.failed` en el timeline del caso. No cambia
 * el estado del caso ni señala Temporal (el run ya terminó).
 */
function QaResolveDialog({
  task,
  mode,
  onOpenChange,
}: {
  task: StaffTask;
  mode: "pass" | "fail";
  onOpenChange: (open: boolean) => void;
}) {
  const resolve = useResolveStaffTaskMutation();
  const [findings, setFindings] = useState("");
  const [error, setError] = useState<string | null>(null);
  const passing = mode === "pass";

  const submit = () => {
    setError(null);
    const trimmed = findings.trim();
    if (!passing && !trimmed) {
      setError("Para marcar como fallida, describe los hallazgos.");
      return;
    }
    const resolution: Record<string, unknown> = { passed: passing };
    if (trimmed) resolution.findings = trimmed;
    resolve.mutate(
      { taskId: task.uuid, resolution },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => setError(backendErrorMessage(e)),
      }
    );
  };

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-md p-6">
        <DialogHeader>
          <DialogTitle>
            {passing ? "Aprobar auditoría QA" : "Marcar QA como fallida"}
          </DialogTitle>
          <DialogDescription>
            {passing
              ? "El caso auto-aprobado pasa la auditoría. Solo se registra el veredicto en el historial."
              : "Registra los hallazgos de la auditoría. El caso ya está completado: esto es medición, no revierte la entrega."}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor={`qa-findings-${task.uuid}`}>
              Hallazgos{passing ? " (opcional)" : ""}
            </Label>
            <Textarea
              id={`qa-findings-${task.uuid}`}
              autoFocus
              rows={4}
              value={findings}
              onChange={(e) => setFindings(e.target.value)}
              placeholder={
                passing
                  ? "Notas de la auditoría para el historial…"
                  : "Qué dejó pasar el modelo o el analista…"
              }
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <ActionButton
            variant={passing ? "success" : "destructive"}
            icon={passing ? <Check /> : <X />}
            loading={resolve.isPending}
            onClick={submit}
          >
            {passing ? "Pasa" : "Falla"}
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

/* ───────────────────────────── vista ───────────────────────────── */

function statusBadge(status: string) {
  if ((Object.values(CaseStatus) as string[]).includes(status)) {
    const config = caseStatusConfig[status as CaseStatus];
    return <Badge variant={config.variant}>{config.label}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function StaffTaskDetailView({ taskId }: { taskId: string }) {
  const pendingQuery = useStaffTasksQuery({ status: "pending" });
  const pendingTask = pendingQuery.data?.find((t) => t.uuid === taskId);
  const resolvedQuery = useStaffTasksQuery(
    { status: "resolved" },
    { enabled: Boolean(pendingQuery.data) && !pendingTask }
  );
  const task =
    pendingTask ?? resolvedQuery.data?.find((t) => t.uuid === taskId);

  const caseQuery = useStaffCaseQuery(task?.caseId);
  const aggregate = caseQuery.data;

  const claim = useClaimStaffTaskMutation();
  const [claimError, setClaimError] = useState<string | null>(null);
  const [dialogMode, setDialogMode] = useState<"approve" | "reject" | null>(
    null
  );
  const [qaMode, setQaMode] = useState<"pass" | "fail" | null>(null);

  const isQa = task?.kind === "qa";
  const myActor = getStaffActor();
  const claimedByOther = Boolean(
    task?.claimedBy && task.claimedBy !== myActor
  );

  const payload = (task?.payload ?? {}) as Record<string, unknown>;
  const verdict = typeof payload.verdict === "string" ? payload.verdict : null;
  const summary = typeof payload.summary === "string" ? payload.summary : null;

  if (pendingQuery.isLoading || (!pendingTask && resolvedQuery.isLoading)) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!task) {
    return (
      <EmptyState
        icon={Inbox}
        title="Tarea no encontrada"
        description="La tarea no está en la cola (puede haber sido resuelta o cancelada)."
      />
    );
  }

  const handleClaim = (release: boolean) => {
    setClaimError(null);
    claim.mutate(
      { taskId: task.uuid, release },
      {
        onSuccess: (updated) => {
          if (!release && updated.claimedBy) {
            rememberStaffActor(updated.claimedBy);
          }
        },
        onError: (e) => setClaimError(backendErrorMessage(e)),
      }
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1.5">
          <Link
            href="/staff"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            {isQa ? "Auditoría QA" : "Cola L1"}
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-semibold tracking-tight">
              {aggregate?.name ?? "Caso"}
            </h1>
            {aggregate && statusBadge(aggregate.status)}
            {isQa ? kindBadge(task.kind) : stageBadge(task.stage)}
            <Badge variant="outline">
              {task.tenantName ?? task.tenantSlug ?? "—"}
            </Badge>
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            {aggregate?.externalRef ?? task.taskKey} ·{" "}
            {formatRelativeDate(task.createdAt)}
          </p>
        </div>

        {task.status === "pending" && isQa && (
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              <ActionButton
                variant="success"
                size="sm"
                icon={<Check />}
                disabled={claimedByOther}
                onClick={() => setQaMode("pass")}
              >
                Pasa
              </ActionButton>
              <ActionButton
                variant="outline"
                size="sm"
                icon={<X />}
                disabled={claimedByOther}
                onClick={() => setQaMode("fail")}
              >
                Falla
              </ActionButton>
            </div>
            {claimedByOther && (
              <p className="text-xs text-muted-foreground">
                Reclamada por {shortActor(task.claimedBy)}
              </p>
            )}
          </div>
        )}

        {task.status === "pending" && !isQa && (
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              {task.claimedBy ? (
                <>
                  <Badge variant={claimedByOther ? "warning" : "success"}>
                    <Lock className="size-3" />
                    {claimedByOther
                      ? `Reclamada por ${shortActor(task.claimedBy)}`
                      : "Reclamada por ti"}
                  </Badge>
                  {!claimedByOther && (
                    <ActionButton
                      variant="ghost"
                      size="sm"
                      icon={<LockOpen />}
                      loading={claim.isPending}
                      onClick={() => handleClaim(true)}
                    >
                      Liberar
                    </ActionButton>
                  )}
                </>
              ) : (
                <ActionButton
                  variant="outline"
                  size="sm"
                  icon={<Lock />}
                  loading={claim.isPending}
                  onClick={() => handleClaim(false)}
                >
                  Reclamar
                </ActionButton>
              )}
              <ActionButton
                variant="success"
                size="sm"
                icon={<Check />}
                disabled={claimedByOther}
                onClick={() => setDialogMode("approve")}
              >
                Aprobar
              </ActionButton>
              <ActionButton
                variant="outline"
                size="sm"
                icon={<X />}
                disabled={claimedByOther}
                onClick={() => setDialogMode("reject")}
              >
                Rechazar
              </ActionButton>
            </div>
            {claimError && (
              <p className="text-xs text-destructive">{claimError}</p>
            )}
          </div>
        )}
        {task.status !== "pending" && (
          <Badge variant="secondary">Resuelta</Badge>
        )}
      </div>

      {(verdict || summary) && (
        <div className="rounded-xl border bg-card p-4 shadow-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">
              Motivo de la revisión
            </span>
            {verdict && <Badge variant="warning">{verdict}</Badge>}
          </div>
          {summary && (
            <p className="mt-1.5 max-w-prose text-sm text-foreground">
              {summary}
            </p>
          )}
        </div>
      )}

      {caseQuery.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : caseQuery.isError ? (
        <p className="text-sm text-destructive">
          {backendErrorMessage(caseQuery.error)}
        </p>
      ) : aggregate ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-4">
            <h2 className="text-sm font-medium text-muted-foreground">
              Documentos ({aggregate.documents.length})
            </h2>
            {aggregate.documents.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                El caso no tiene documentos.
              </p>
            ) : (
              aggregate.documents.map((doc) => (
                <StaffDocumentCard key={doc.documentId} document={doc} />
              ))
            )}
          </div>
          <div className="space-y-4">
            {aggregate.latestOutput && (
              <div className="rounded-xl border bg-card p-4 shadow-xs">
                <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                  Último análisis
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  {aggregate.latestOutput.verdict && (
                    <Badge
                      variant={
                        aggregate.latestOutput.verdict
                          .toLowerCase()
                          .includes("pass")
                          ? "success"
                          : "warning"
                      }
                    >
                      {aggregate.latestOutput.verdict}
                    </Badge>
                  )}
                  {aggregate.latestOutput.confidenceScore != null && (
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {Math.round(aggregate.latestOutput.confidenceScore * 100)}
                      % confianza
                    </span>
                  )}
                </div>
              </div>
            )}
            <div className="rounded-xl border bg-card p-4 shadow-xs">
              <h2 className="mb-3 text-sm font-medium text-muted-foreground">
                Historial del caso
              </h2>
              <CaseTimeline events={(aggregate.timeline ?? []) as CaseEvent[]} />
            </div>
          </div>
        </div>
      ) : null}

      {dialogMode && (
        <ResolveDialog
          task={task}
          mode={dialogMode}
          onOpenChange={(open) => {
            if (!open) setDialogMode(null);
          }}
        />
      )}
      {qaMode && (
        <QaResolveDialog
          task={task}
          mode={qaMode}
          onOpenChange={(open) => {
            if (!open) setQaMode(null);
          }}
        />
      )}
    </div>
  );
}
