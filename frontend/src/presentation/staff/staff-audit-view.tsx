"use client";

import { RefreshCw, ScrollText, ShieldAlert } from "lucide-react";
import { useState } from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import {
  backendErrorMessage,
  useStaffAuditQuery,
} from "@/src/application/hooks/queries/staff-tasks";
import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";

function shortId(value: string | null): string {
  return value ? value.slice(0, 8) : "—";
}

/**
 * E5 · audit de accesos staff (solo `staff_admin`; el backend devuelve 403
 * para el resto — el gate de UI usa `user.staffRole` del payload de sesión).
 */
export function StaffAuditView() {
  const staffRole = useSessionStore((s) => s.user?.staffRole ?? null);
  const isAdmin = staffRole === "staff_admin";
  const [action, setAction] = useState("");

  const auditQuery = useStaffAuditQuery(
    { limit: 100, ...(action.trim() ? { action: action.trim() } : {}) },
    { enabled: isAdmin }
  );

  if (!isAdmin) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Solo staff admin"
        description="La auditoría de accesos requiere el rol staff_admin."
      />
    );
  }

  const events = auditQuery.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Auditoría de accesos
          </h1>
          <p className="text-sm text-muted-foreground">
            Cada request a la consola staff queda registrada (100 % por
            construcción).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={action}
            onChange={(e) => setAction(e.target.value)}
            placeholder="Filtrar por acción…"
            className="h-8 w-48"
          />
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => auditQuery.refetch()}
            aria-label="Refrescar"
          >
            <RefreshCw className="size-4" />
          </Button>
        </div>
      </div>

      {auditQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={`audit-skeleton-${i + 1}`} className="h-10 w-full" />
          ))}
        </div>
      ) : auditQuery.isError ? (
        <p className="text-sm text-destructive">
          {backendErrorMessage(auditQuery.error)}
        </p>
      ) : events.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="Sin eventos"
          description="Aún no hay accesos registrados con ese filtro."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cuándo</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Staff</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Caso</TableHead>
                <TableHead>Tarea</TableHead>
                <TableHead>IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.uuid}>
                  <TableCell
                    className="whitespace-nowrap text-sm text-muted-foreground"
                    title={event.createdAt ?? undefined}
                  >
                    {formatRelativeDate(event.createdAt)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono text-xs">
                      {event.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {shortId(event.staffUserId)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {shortId(event.tenantId)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {shortId(event.caseId)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {shortId(event.taskId)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {event.ip ?? "—"}
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
