"use client";

import {
  ArrowUpRight,
  Check,
  ChevronDown,
  Eye,
  Inbox,
  Lock,
  LockOpen,
  MessageCircleQuestion,
  ShieldAlert,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useSessionStore } from "@/src/application/contexts/session-store";
import {
  type HumanTask,
  HumanTaskClaimedError,
  HumanTaskOpenFlagsError,
  type OpenFlagField,
  useClaimHumanTaskMutation,
  useHumanTasksQuery,
  useResolveHumanTaskMutation,
} from "@/src/application/hooks/queries/human-tasks";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/src/presentation/components/ui/collapsible";
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
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { Textarea } from "@/src/presentation/components/ui/textarea";

/** Actor del usuario en sesión con el formato del backend (`user:<uuid>`). */
function useSessionActor(): string | null {
  const uuid = useSessionStore((s) => s.user?.uuid ?? null);
  return uuid ? `user:${uuid}` : null;
}

/* ────────────────────────── helpers de payload ────────────────────────── */

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/**
 * Items de aclaración según el contrato E4 (`clarification.requested`):
 * `{ fieldPath, reason, parseConfidence, signals, candidates, page }`.
 * Todos opcionales: el payload viene del backend en construcción, así que
 * se leen de forma tolerante campo a campo.
 */
function clarificationItems(task: HumanTask): Record<string, unknown>[] {
  const items = task.payload?.items;
  if (!Array.isArray(items)) return [];
  return items
    .map(asRecord)
    .filter((item): item is Record<string, unknown> => item !== null);
}

function signalLabels(signals: unknown): string[] {
  if (Array.isArray(signals)) {
    return signals.map((s) => (typeof s === "string" ? s : JSON.stringify(s)));
  }
  const rec = asRecord(signals);
  if (rec) return Object.entries(rec).map(([k, v]) => `${k}: ${String(v)}`);
  return [];
}

function confidencePct(value: unknown): string | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  return `${Math.round(value * 100)}%`;
}

const KIND_CONFIG: Record<
  string,
  { label: string; icon: typeof Eye; className: string }
> = {
  approval: {
    label: "Aprobación",
    icon: Eye,
    className:
      "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/40 dark:text-violet-200 dark:border-violet-800",
  },
  clarification: {
    label: "Aclaración",
    icon: MessageCircleQuestion,
    className:
      "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800",
  },
};

function KindBadge({ kind }: { kind: string }) {
  const cfg = KIND_CONFIG[kind];
  if (!cfg) return <Badge variant="secondary">{kind}</Badge>;
  const Icon = cfg.icon;
  return (
    <Badge variant="outline" className={cfg.className}>
      <Icon />
      {cfg.label}
    </Badge>
  );
}

/* ───────────────── E5 · stages + claim/lock pesimista ───────────────── */

const STAGE_LABEL: Record<string, string> = {
  review_l1: "L1 · Doxiq",
  review_l2: "L2",
};

function StageBadge({ stage }: { stage: string | null }) {
  if (!stage) return null;
  return (
    <Badge variant="secondary" className="font-mono text-[10px] uppercase">
      {STAGE_LABEL[stage] ?? stage}
    </Badge>
  );
}

/** Holder legible: «por ti» o el actor corto (`user:1a2b3c4d…`). */
function holderLabel(holder: string, actor: string | null): string {
  if (actor && holder === actor) return "por ti";
  const [kind, id] = holder.split(":");
  return `por ${kind === "staff" ? "staff" : "usuario"} ${id?.slice(0, 8) ?? holder}`;
}

/**
 * E5 §3.2 · botón Reclamar / Liberar + holder visible. El claim bloquea la
 * edición del caso para otros (lock pesimista); 409 ⇒ holder en el error.
 */
function ClaimControls({ task }: { task: HumanTask }) {
  const claim = useClaimHumanTaskMutation();
  const actor = useSessionActor();
  const [error, setError] = useState<string | null>(null);

  const claimedByMe = task.claimedBy !== null && task.claimedBy === actor;
  const claimedByOther = task.claimedBy !== null && !claimedByMe;

  const run = (release: boolean) => {
    setError(null);
    claim.mutate(
      { id: task.uuid, release },
      {
        onError: (e) =>
          setError(
            e instanceof HumanTaskClaimedError && e.holder
              ? `Reclamada ${holderLabel(e.holder, actor)}.`
              : e.message
          ),
      }
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {task.claimedBy ? (
        <Badge variant={claimedByMe ? "success" : "warning"} className="gap-1">
          <Lock className="size-3" />
          Reclamada {holderLabel(task.claimedBy, actor)}
        </Badge>
      ) : null}
      {claimedByMe ? (
        <ActionButton
          size="xs"
          variant="outline"
          icon={<LockOpen />}
          loading={claim.isPending}
          onClick={() => run(true)}
        >
          Liberar
        </ActionButton>
      ) : !claimedByOther ? (
        <ActionButton
          size="xs"
          variant="outline"
          icon={<Lock />}
          loading={claim.isPending}
          onClick={() => run(false)}
        >
          Reclamar
        </ActionButton>
      ) : null}
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

function CaseLink({ task }: { task: HumanTask }) {
  if (!task.caseId) return null;
  const short = task.caseId.slice(0, 8);
  // El segmento [wfSlug] transporta el UUID del workflow (los endpoints
  // backend declaran workflow_id: UUID) — navegar por slug da 422.
  if (!task.workflowId) {
    return (
      <span className="font-mono text-xs text-muted-foreground">
        caso {short}
      </span>
    );
  }
  return (
    <Link
      href={`/workflows/${task.workflowId}/cases/${task.caseId}`}
      className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
    >
      Ver caso <span className="font-mono text-xs">{short}</span>
      <ArrowUpRight className="size-3.5" />
    </Link>
  );
}

function TechnicalDetails({ payload }: { payload: HumanTask["payload"] }) {
  if (!payload || Object.keys(payload).length === 0) return null;
  return (
    <Collapsible>
      <CollapsibleTrigger className="group flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ChevronDown className="size-3.5 transition-transform group-data-[panel-open]:rotate-180" />
        Detalles técnicos
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="mt-2 max-h-48 overflow-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed text-muted-foreground">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
}

/* ─────────────────────────── aprobaciones ─────────────────────────── */

function verdictBadgeVariant(
  verdict: string
): "success" | "destructive" | "secondary" {
  const v = verdict.toLowerCase();
  if (["passed", "pass", "approved", "ok", "success"].includes(v))
    return "success";
  if (["failed", "fail", "rejected", "blocker", "error"].includes(v))
    return "destructive";
  return "secondary";
}

function ApprovalResolveDialog({
  task,
  mode,
  open,
  onOpenChange,
}: {
  task: HumanTask;
  mode: "approve" | "reject";
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const resolve = useResolveHumanTaskMutation();
  const actor = useSessionActor();
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  // E5 §3.4 · 409 `human_task.open_flags`: campos flageados sin verificar.
  // El dialog cambia a modo force con la lista.
  const [openFlags, setOpenFlags] = useState<OpenFlagField[] | null>(null);
  const approving = mode === "approve";

  const handleSubmit = (force = false) => {
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
      { id: task.uuid, resolution },
      {
        onSuccess: () => {
          setComment("");
          setOpenFlags(null);
          onOpenChange(false);
        },
        onError: (e) => {
          if (e instanceof HumanTaskOpenFlagsError) {
            setOpenFlags(e.openFields);
            return;
          }
          if (e instanceof HumanTaskClaimedError && e.holder) {
            setError(
              `La tarea está reclamada ${holderLabel(e.holder, actor)}.`
            );
            return;
          }
          setError(e.message);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-md p-6">
        <DialogHeader>
          <DialogTitle>
            {openFlags
              ? "Hay campos sin verificar"
              : approving
                ? "Aprobar caso"
                : "Rechazar caso"}
          </DialogTitle>
          <DialogDescription>
            {openFlags
              ? "Estos campos siguen flageados sin verificación. Verifícalos en el bench o aprueba de todos modos."
              : approving
                ? "El caso continuará con la generación y entrega del resultado."
                : "El caso quedará rechazado y no se generará ni entregará el resultado."}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-2">
          {openFlags ? (
            <ul className="max-h-56 space-y-1.5 overflow-auto">
              {openFlags.map((field) => (
                <li
                  key={`${field.documentId}:${field.fieldPath}`}
                  className="flex items-center justify-between gap-3 rounded-md bg-warning/10 px-3 py-2"
                >
                  <span className="font-mono text-xs font-medium">
                    {field.fieldPath}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    doc {field.documentId.slice(0, 8)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <>
              <Label htmlFor={`comment-${task.uuid}`}>
                Comentario{approving ? " (opcional)" : ""}
              </Label>
              <Textarea
                id={`comment-${task.uuid}`}
                autoFocus
                rows={4}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={
                  approving
                    ? "Notas para el historial del caso…"
                    : "Motivo del rechazo…"
                }
              />
            </>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </DialogBody>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() =>
              openFlags ? setOpenFlags(null) : onOpenChange(false)
            }
          >
            {openFlags ? "Volver" : "Cancelar"}
          </Button>
          {openFlags ? (
            <ActionButton
              variant="destructive"
              icon={<ShieldAlert />}
              loading={resolve.isPending}
              onClick={() => handleSubmit(true)}
            >
              Aprobar de todos modos
            </ActionButton>
          ) : (
            <ActionButton
              variant={approving ? "success" : "destructive"}
              icon={approving ? <Check /> : <X />}
              loading={resolve.isPending}
              onClick={() => handleSubmit()}
            >
              {approving ? "Aprobar" : "Rechazar"}
            </ActionButton>
          )}
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function ApprovalCard({ task }: { task: HumanTask }) {
  const [dialogMode, setDialogMode] = useState<"approve" | "reject" | null>(
    null
  );
  const actor = useSessionActor();
  const payload = task.payload ?? {};
  const verdict = typeof payload.verdict === "string" ? payload.verdict : null;
  const summary = typeof payload.summary === "string" ? payload.summary : null;
  const signals = signalLabels(payload.signals);

  // E5 · L1 se resuelve en la consola staff de Doxiq: la cola tenant lo
  // muestra informativo, sin acciones (el backend respondería 403).
  const staffOnly = task.stage === "review_l1";
  const claimedByOther =
    task.claimedBy !== null && (!actor || task.claimedBy !== actor);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <KindBadge kind={task.kind} />
            <StageBadge stage={task.stage} />
            {verdict && (
              <Badge variant={verdictBadgeVariant(verdict)}>{verdict}</Badge>
            )}
            <span className="text-xs text-muted-foreground">
              {formatRelativeDate(task.createdAt)}
            </span>
          </div>
          <CardTitle className="truncate text-sm">{task.taskKey}</CardTitle>
        </div>
        <CaseLink task={task} />
      </CardHeader>
      <CardContent className="space-y-4">
        {summary && (
          <p className="max-w-prose text-sm text-foreground">{summary}</p>
        )}
        {signals.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {signals.map((signal) => (
              <Badge key={signal} variant="warning">
                {signal}
              </Badge>
            ))}
          </div>
        )}
        <TechnicalDetails payload={task.payload} />
        {staffOnly ? (
          <p className="text-sm text-muted-foreground">
            En revisión por el equipo Doxiq (L1). Pasará a tu cola cuando
            termine.
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <ActionButton
              variant="success"
              icon={<Check />}
              disabled={claimedByOther}
              title={
                claimedByOther
                  ? "Otro analista tiene reclamada esta tarea."
                  : undefined
              }
              onClick={() => setDialogMode("approve")}
            >
              Aprobar
            </ActionButton>
            <ActionButton
              variant="outline"
              icon={<X />}
              disabled={claimedByOther}
              title={
                claimedByOther
                  ? "Otro analista tiene reclamada esta tarea."
                  : undefined
              }
              onClick={() => setDialogMode("reject")}
            >
              Rechazar
            </ActionButton>
            <ClaimControls task={task} />
          </div>
        )}
        {dialogMode && (
          <ApprovalResolveDialog
            task={task}
            mode={dialogMode}
            open
            onOpenChange={(open) => {
              if (!open) setDialogMode(null);
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────── aclaraciones ─────────────────────────── */

function ClarificationItemRow({ item }: { item: Record<string, unknown> }) {
  const fieldPath =
    typeof item.fieldPath === "string" ? item.fieldPath : "(campo)";
  const reason = typeof item.reason === "string" ? item.reason : null;
  const pct =
    confidencePct(item.parseConfidence) ??
    confidencePct(item.extractConfidence);
  const page = typeof item.page === "number" ? item.page : null;
  const candidates = Array.isArray(item.candidates) ? item.candidates : [];
  const signals = signalLabels(item.signals);

  return (
    <li className="space-y-1.5 rounded-md bg-muted/40 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs font-medium">{fieldPath}</span>
        {pct && <Badge variant="warning">confianza {pct}</Badge>}
        {page !== null && (
          <span className="text-xs text-muted-foreground">pág. {page}</span>
        )}
      </div>
      {reason && <p className="text-sm text-muted-foreground">{reason}</p>}
      {signals.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {signals.map((signal) => (
            <Badge key={signal} variant="outline">
              {signal}
            </Badge>
          ))}
        </div>
      )}
      {candidates.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Candidatos:</span>
          {candidates.map((candidate, idx) => (
            <Badge key={idx} variant="secondary" className="font-mono">
              {typeof candidate === "string"
                ? candidate
                : JSON.stringify(candidate)}
            </Badge>
          ))}
        </div>
      )}
    </li>
  );
}

function GenericResolveDialog({
  task,
  open,
  onOpenChange,
}: {
  task: HumanTask;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const resolve = useResolveHumanTaskMutation();
  const [value, setValue] = useState("{}");
  const [error, setError] = useState<string | null>(null);
  const items = clarificationItems(task);

  const handleResolve = () => {
    setError(null);
    let resolution: Record<string, unknown>;
    try {
      const parsed = JSON.parse(value);
      if (
        typeof parsed !== "object" ||
        parsed === null ||
        Array.isArray(parsed)
      ) {
        throw new Error("El JSON debe ser un objeto.");
      }
      resolution = parsed as Record<string, unknown>;
    } catch (e) {
      setError(e instanceof Error ? e.message : "JSON inválido.");
      return;
    }
    resolve.mutate(
      { id: task.uuid, resolution },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => setError(e.message),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-lg p-6">
        <DialogHeader>
          <DialogTitle>Resolver aclaración</DialogTitle>
          <DialogDescription>
            Revisa los campos señalados y envía la resolución al flujo en
            espera.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-3">
          {items.length > 0 && (
            <ul className="max-h-64 space-y-2 overflow-auto">
              {items.map((item, idx) => (
                <ClarificationItemRow key={idx} item={item} />
              ))}
            </ul>
          )}
          <Collapsible defaultOpen={items.length === 0}>
            <CollapsibleTrigger className="group flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3.5 transition-transform group-data-[panel-open]:rotate-180" />
              Avanzado
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2 space-y-2">
                <Label htmlFor={`resolution-json-${task.uuid}`}>
                  Resolución (JSON)
                </Label>
                <Textarea
                  id={`resolution-json-${task.uuid}`}
                  rows={5}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder='{"answer": "..."}'
                  className="font-mono text-sm"
                />
              </div>
            </CollapsibleContent>
          </Collapsible>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <ActionButton loading={resolve.isPending} onClick={handleResolve}>
            Enviar resolución
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function ClarificationCard({ task }: { task: HumanTask }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const items = clarificationItems(task);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <KindBadge kind={task.kind} />
            <span className="text-xs text-muted-foreground">
              {formatRelativeDate(task.createdAt)}
            </span>
          </div>
          <CardTitle className="truncate text-sm">{task.taskKey}</CardTitle>
        </div>
        <CaseLink task={task} />
      </CardHeader>
      <CardContent className="space-y-4">
        {items.length > 0 ? (
          <ul className="space-y-2">
            {items.slice(0, 3).map((item, idx) => (
              <ClarificationItemRow key={idx} item={item} />
            ))}
            {items.length > 3 && (
              <li className="text-xs text-muted-foreground">
                y {items.length - 3} más…
              </li>
            )}
          </ul>
        ) : (
          <TechnicalDetails payload={task.payload} />
        )}
        <Button variant="default" onClick={() => setDialogOpen(true)}>
          Resolver
        </Button>
        <GenericResolveDialog
          task={task}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      </CardContent>
    </Card>
  );
}

/* ────────────────────────────── vista ────────────────────────────── */

function TaskCard({ task }: { task: HumanTask }) {
  if (task.kind === "approval") return <ApprovalCard task={task} />;
  return <ClarificationCard task={task} />;
}

type QueueTab = "all" | "review_l1" | "review_l2";

const QUEUE_TABS: Array<{ value: QueueTab; label: string }> = [
  { value: "all", label: "Todas" },
  { value: "review_l1", label: "Revisión L1" },
  { value: "review_l2", label: "Revisión L2" },
];

export function ReviewQueueView() {
  const { data: tasks, isLoading } = useHumanTasksQuery();
  const [activeQueue, setActiveQueue] = useState<QueueTab>("all");

  const openTasks = useMemo(
    () =>
      (tasks ?? []).filter(
        (t) => t.status === "open" || t.status === "pending"
      ),
    [tasks]
  );

  // E5 · colas por stage con contadores; las tareas sin stage (aclaraciones,
  // aprobaciones legacy) solo viven en «Todas».
  const counts = useMemo<Record<QueueTab, number>>(
    () => ({
      all: openTasks.length,
      review_l1: openTasks.filter((t) => t.stage === "review_l1").length,
      review_l2: openTasks.filter((t) => t.stage === "review_l2").length,
    }),
    [openTasks]
  );

  const visibleTasks = useMemo(
    () =>
      activeQueue === "all"
        ? openTasks
        : openTasks.filter((t) => t.stage === activeQueue),
    [openTasks, activeQueue]
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight">Revisión</h2>
        <p className="text-sm text-muted-foreground">
          Tareas humanas pendientes generadas por los flujos: aprobaciones y
          aclaraciones que requieren tu intervención.
        </p>
      </div>

      <Tabs
        value={activeQueue}
        onValueChange={(value) => setActiveQueue(value as QueueTab)}
      >
        <TabsList
          variant="line"
          className="w-full justify-start bg-transparent"
        >
          {QUEUE_TABS.map((tab) => (
            <TabsTrigger
              key={tab.value}
              variant="line"
              value={tab.value}
              className="gap-2"
            >
              <span className="text-sm">{tab.label}</span>
              {counts[tab.value] > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {counts[tab.value]}
                </Badge>
              )}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <Card>
          <CardContent className="py-8">
            <p className="text-sm text-muted-foreground">Cargando…</p>
          </CardContent>
        </Card>
      ) : visibleTasks.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Bandeja de revisión</CardTitle>
            <CardDescription>
              Aquí aparecerán las tareas que esperan una decisión.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <Inbox className="size-8 text-muted-foreground/60" />
            <p className="text-sm font-medium">Bandeja limpia</p>
            <p className="text-sm text-muted-foreground">
              {activeQueue === "all"
                ? "No hay tareas pendientes. Cuando un flujo solicite una revisión o una aclaración, la verás aquí."
                : "No hay tareas pendientes en esta cola."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {visibleTasks.map((task) => (
            <TaskCard key={task.uuid} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}
