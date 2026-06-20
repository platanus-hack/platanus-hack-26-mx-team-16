"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Split } from "lucide-react";
import Link from "next/link";

import { queryKeys } from "@/src/application/hooks/queries/keys";
import {
  CaseStatus,
  type CaseChildrenSummary,
} from "@/src/domain/entities/case";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpCaseRepository } from "@/src/infrastructure/repositories/http-case";
import { Badge } from "@/src/presentation/components/ui/badge";
import { caseStatusConfig } from "./case-status-config";

const repo = new HttpCaseRepository(authHttp);

interface Props {
  workflowUuid: string;
  caseId: string;
  summary: CaseChildrenSummary;
}

function statusChip(status: string, count: number) {
  const cfg = (Object.values(CaseStatus) as string[]).includes(status)
    ? caseStatusConfig[status as CaseStatus]
    : null;
  if (!cfg) {
    return (
      <Badge key={status} variant="secondary">
        {count} {status}
      </Badge>
    );
  }
  const Icon = cfg.icon;
  return (
    <Badge key={status} variant={cfg.variant} className={cfg.className}>
      <Icon />
      {count} {cfg.label}
    </Badge>
  );
}

/**
 * E5 · fan-out: panel de children en el detalle del caso padre. Total +
 * chips por estado + lista con link a cada child. La lista usa el filtro
 * `parentCaseId` del listado de casos (query param del backend).
 */
export function CaseChildrenPanel({ workflowUuid, caseId, summary }: Props) {
  const { data: childrenPage } = useQuery({
    queryKey: queryKeys.cases.children(workflowUuid, caseId),
    queryFn: async () => {
      const res = await repo.getPaginated(workflowUuid, {
        parentCaseId: caseId,
        limit: 100,
      });
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res;
    },
    enabled: summary.total > 0,
  });

  if (summary.total === 0) return null;

  const childCases = childrenPage?.data ?? [];

  return (
    <section
      aria-label="Casos derivados"
      className="mb-4 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/10"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Split className="size-4 text-muted-foreground" />
          <h3 className="text-sm font-medium">
            Casos derivados del split
            <span className="ml-1.5 font-mono text-xs text-muted-foreground">
              {summary.total}
            </span>
          </h3>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(summary.byStatus).map(([status, count]) =>
            statusChip(status, count ?? 0)
          )}
        </div>
      </div>

      {childCases.length > 0 && (
        <ul className="mt-3 divide-y divide-border/60">
          {childCases.map((child) => {
            const cfg = caseStatusConfig[child.status];
            const Icon = cfg?.icon;
            return (
              <li key={child.uuid}>
                <Link
                  href={`/workflows/${workflowUuid}/cases/${child.uuid}`}
                  className="group flex items-center justify-between gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/60"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium">
                      {child.name}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {child.uuid.slice(0, 8)}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {cfg && (
                      <Badge variant={cfg.variant} className={cfg.className}>
                        {Icon ? <Icon /> : null}
                        {cfg.label}
                      </Badge>
                    )}
                    <ArrowUpRight className="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      {childrenPage?.pagination?.nextCursor && (
        <p className="mt-2 text-xs text-muted-foreground">
          Mostrando {childCases.length} de {summary.total} casos.
        </p>
      )}
    </section>
  );
}
