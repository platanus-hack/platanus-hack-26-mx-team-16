"use client";

import { Inbox, Lock, LockOpen, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  backendErrorMessage,
  useClaimStaffTaskMutation,
  useStaffTasksQuery,
  type StaffTask,
} from "@/src/application/hooks/queries/staff-tasks";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { getStaffActor, rememberStaffActor } from "./staff-actor";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/src/presentation/components/ui/toggle-group";

/** `staff:1a2b3c4d-…` → `1a2b3c` (suficiente para distinguir holders). */
export function shortActor(actor: string | null | undefined): string {
  if (!actor) return "—";
  const id = actor.split(":")[1] ?? actor;
  return id.slice(0, 6);
}

export function stageBadge(stage: string | null) {
  if (stage === "review_l1") return <Badge variant="default">L1</Badge>;
  if (stage === "review_l2") return <Badge variant="secondary">L2</Badge>;
  return null;
}

/** E6 §3 — badge del tipo de cola (QA vs aprobación). */
export function kindBadge(kind: string | null | undefined) {
  if (kind === "qa") return <Badge variant="warning">QA</Badge>;
  return null;
}

function ClaimCell({ task }: { task: StaffTask }) {
  const claim = useClaimStaffTaskMutation();
  const [error, setError] = useState<string | null>(null);
  // localStorage solo tras montar (evita mismatch de hidratación SSR).
  const [myActor, setMyActor] = useState<string | null>(null);
  useEffect(() => setMyActor(getStaffActor()), []);
  const claimed = Boolean(task.claimedBy);
  const mine = claimed && task.claimedBy === myActor;

  if (task.status !== "pending") {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  const handle = (release: boolean) => {
    setError(null);
    claim.mutate(
      { taskId: task.uuid, release },
      {
        onSuccess: (updated) => {
          if (!release && updated.claimedBy) {
            rememberStaffActor(updated.claimedBy);
            setMyActor(updated.claimedBy);
          }
        },
        onError: (e) => setError(backendErrorMessage(e)),
      }
    );
  };

  return (
    <div className="flex flex-col items-start gap-1">
      {claimed ? (
        <div className="flex items-center gap-2">
          <Badge variant={mine ? "success" : "warning"}>
            <Lock className="size-3" />
            {mine ? "Tuya" : shortActor(task.claimedBy)}
          </Badge>
          {mine && (
            <ActionButton
              variant="ghost"
              size="xs"
              icon={<LockOpen />}
              loading={claim.isPending}
              onClick={() => handle(true)}
            >
              Liberar
            </ActionButton>
          )}
        </div>
      ) : (
        <ActionButton
          variant="outline"
          size="xs"
          icon={<Lock />}
          loading={claim.isPending}
          onClick={() => handle(false)}
        >
          Reclamar
        </ActionButton>
      )}
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

export function StaffQueueView() {
  const [status, setStatus] = useState<"pending" | "resolved">("pending");
  const [kind, setKind] = useState<"approval" | "qa">("approval");
  const [tenantFilter, setTenantFilter] = useState<string>("all");

  const tasksQuery = useStaffTasksQuery({ status, kind });
  const tasks = tasksQuery.data ?? [];
  const isQa = kind === "qa";

  const tenants = useMemo(() => {
    const map = new Map<string, string>();
    for (const t of tasks) {
      map.set(t.tenantId, t.tenantName ?? t.tenantSlug ?? t.tenantId);
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [tasks]);

  const visible = useMemo(
    () =>
      tenantFilter === "all"
        ? tasks
        : tasks.filter((t) => t.tenantId === tenantFilter),
    [tasks, tenantFilter]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            {isQa ? "Auditoría QA" : "Cola de revisión L1"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isQa
              ? "Casos auto-aprobados muestreados para auditoría post-completado. Resuelve con un veredicto pass/fail."
              : "Tareas de revisión interna de todos los tenants. Reclama una tarea antes de trabajarla."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup
            value={[kind]}
            onValueChange={(value: string[]) => {
              const next = value[0];
              if (next === "approval" || next === "qa") setKind(next);
            }}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="approval">Aprobaciones</ToggleGroupItem>
            <ToggleGroupItem value="qa">QA</ToggleGroupItem>
          </ToggleGroup>
          <ToggleGroup
            value={[status]}
            onValueChange={(value: string[]) => {
              const next = value[0];
              if (next === "pending" || next === "resolved") setStatus(next);
            }}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="pending">Pendientes</ToggleGroupItem>
            <ToggleGroupItem value="resolved">Resueltas</ToggleGroupItem>
          </ToggleGroup>
          {tenants.length > 1 && (
            <Select
              value={tenantFilter}
              onValueChange={(value) => setTenantFilter(value ?? "all")}
            >
              <SelectTrigger size="sm" className="w-44">
                <SelectValue placeholder="Tenant" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los tenants</SelectItem>
                {tenants.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => tasksQuery.refetch()}
            aria-label="Refrescar"
          >
            <RefreshCw className="size-4" />
          </Button>
        </div>
      </div>

      {tasksQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={`queue-skeleton-${i + 1}`} className="h-12 w-full" />
          ))}
        </div>
      ) : tasksQuery.isError ? (
        <p className="text-sm text-destructive">
          {backendErrorMessage(tasksQuery.error)}
        </p>
      ) : visible.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Sin tareas en la cola"
          description={
            status === "pending"
              ? isQa
                ? "No hay auditorías QA pendientes en ningún tenant."
                : "No hay revisiones L1 pendientes en ningún tenant."
              : "No hay tareas resueltas para mostrar."
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tenant</TableHead>
                <TableHead>Tarea</TableHead>
                <TableHead>Cola</TableHead>
                <TableHead>Antigüedad</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Lock</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((task) => (
                <TableRow key={task.uuid}>
                  <TableCell>
                    <Badge variant="outline">
                      {task.tenantName ?? task.tenantSlug ?? "—"}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-64">
                    <Link
                      href={`/staff/tasks/${task.uuid}`}
                      className="block truncate font-mono text-xs text-foreground hover:underline"
                      title={task.taskKey}
                    >
                      {task.taskKey}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {isQa ? kindBadge(task.kind) : stageBadge(task.stage)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatRelativeDate(task.createdAt)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        task.status === "pending" ? "warning" : "secondary"
                      }
                    >
                      {task.status === "pending" ? "Pendiente" : task.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <ClaimCell task={task} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/staff/tasks/${task.uuid}`}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      Abrir
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
