"use client";

import { Lock, LockOpen, OctagonAlert, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";

import {
  useClaimHumanTaskMutation,
  useHumanTasksQuery,
  type HumanTask,
} from "@/src/application/hooks/queries/human-tasks";
import { useSessionStore } from "@/src/application/contexts/session-store";
import type { AnalysisRuleResult } from "@/src/domain/entities/analysis-run";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";

interface Props {
  caseId: string;
  /** Resultados del último análisis cargado (para resolver ruleId → nombre). */
  results?: AnalysisRuleResult[];
}

interface GateItem {
  documentId: string | null;
  fieldPath: string;
  reason: string | null;
}

function parseGateItems(task: HumanTask): GateItem[] {
  const items = task.payload?.items;
  if (!Array.isArray(items)) return [];
  return items
    .filter(
      (item): item is Record<string, unknown> =>
        typeof item === "object" && item !== null
    )
    .map((item) => ({
      documentId: typeof item.documentId === "string" ? item.documentId : null,
      fieldPath: typeof item.fieldPath === "string" ? item.fieldPath : "",
      reason: typeof item.reason === "string" ? item.reason : null,
    }))
    .filter((item) => item.fieldPath);
}

interface BlockerSignal {
  ruleId: string;
  label: string;
}

function parseBlockerSignals(
  task: HumanTask,
  results: AnalysisRuleResult[]
): BlockerSignal[] {
  const signals = task.payload?.signals;
  if (!Array.isArray(signals)) return [];
  const nameByRule = new Map(
    results.map((r) => [r.ruleId, r.ruleName ?? null])
  );
  return signals
    .filter(
      (s): s is Record<string, unknown> => typeof s === "object" && s !== null
    )
    .filter(
      (s) =>
        typeof s.severity === "string" &&
        s.severity.toUpperCase() === "BLOCKER" &&
        (typeof s.polarity !== "string" ||
          !["positive", "pass"].includes(s.polarity.toLowerCase()))
    )
    .map((s) => {
      const ruleId = typeof s.ruleId === "string" ? s.ruleId : "";
      return {
        ruleId,
        label: nameByRule.get(ruleId) ?? `regla ${ruleId.slice(0, 8)}`,
      };
    });
}

const STAGE_LABEL: Record<string, string> = {
  review_l1: "Revisión L1 (Doxiq)",
  review_l2: "Revisión L2",
};

/**
 * E5 · «Este caso está aquí porque…»: panel de bloqueadores del detalle de
 * caso. Agrega los gate items (campos por verificar) y las reglas BLOCKER del
 * último análisis desde el payload de la APPROVAL abierta, y hace visible el
 * lock pesimista (holder del claim) con botón Reclamar/Liberar.
 */
export function CaseBlockersPanel({ caseId, results = [] }: Props) {
  const { data: tasks } = useHumanTasksQuery();
  const claim = useClaimHumanTaskMutation();
  const currentUserUuid = useSessionStore((s) => s.user?.uuid ?? null);
  const [claimError, setClaimError] = useState<string | null>(null);

  const task = useMemo(
    () =>
      (tasks ?? []).find(
        (t) =>
          t.caseId === caseId &&
          t.kind === "approval" &&
          (t.status === "pending" || t.status === "open")
      ) ?? null,
    [tasks, caseId]
  );

  const gateItems = useMemo(
    () => (task ? parseGateItems(task) : []),
    [task]
  );
  const blockers = useMemo(
    () => (task ? parseBlockerSignals(task, results) : []),
    [task, results]
  );

  if (!task) return null;

  const actor = currentUserUuid ? `user:${currentUserUuid}` : null;
  const claimedByMe = task.claimedBy !== null && task.claimedBy === actor;
  const claimedByOther = task.claimedBy !== null && !claimedByMe;
  const verdict =
    typeof task.payload?.verdict === "string" ? task.payload.verdict : null;
  const stageLabel = task.stage ? (STAGE_LABEL[task.stage] ?? task.stage) : null;

  const handleClaim = (release: boolean) => {
    setClaimError(null);
    claim.mutate(
      { id: task.uuid, release },
      { onError: (e) => setClaimError(e.message) }
    );
  };

  return (
    <section
      aria-label="Bloqueadores del caso"
      className="mb-4 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/10"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-warning" />
          <h3 className="text-sm font-medium">Este caso está aquí porque…</h3>
          {stageLabel && <Badge variant="secondary">{stageLabel}</Badge>}
          {verdict && (
            <Badge
              variant={
                verdict.toUpperCase() === "FAIL" ? "destructive" : "warning"
              }
            >
              {verdict}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {claimedByOther && (
            <Badge variant="warning" className="gap-1">
              <Lock className="size-3" />
              Reclamada por{" "}
              <span className="font-mono">{task.claimedBy}</span>
            </Badge>
          )}
          {claimedByMe ? (
            <ActionButton
              size="xs"
              variant="outline"
              icon={<LockOpen />}
              loading={claim.isPending}
              onClick={() => handleClaim(true)}
            >
              Liberar
            </ActionButton>
          ) : !claimedByOther && task.stage !== "review_l1" ? (
            <ActionButton
              size="xs"
              variant="outline"
              icon={<Lock />}
              loading={claim.isPending}
              onClick={() => handleClaim(false)}
            >
              Reclamar
            </ActionButton>
          ) : null}
        </div>
      </div>

      {(blockers.length > 0 || gateItems.length > 0) && (
        <div className="mt-3 space-y-2">
          {blockers.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-muted-foreground">
                Reglas bloqueantes:
              </span>
              {blockers.map((b) => (
                <Badge key={b.ruleId} variant="destructive" className="gap-1">
                  <OctagonAlert className="size-3" />
                  {b.label}
                </Badge>
              ))}
            </div>
          )}
          {gateItems.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-muted-foreground">
                Campos por verificar:
              </span>
              {gateItems.map((item) => (
                <Badge
                  key={`${item.documentId}:${item.fieldPath}`}
                  variant="warning"
                  className="font-mono"
                  title={item.reason ?? undefined}
                >
                  {item.fieldPath}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      {claimError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {claimError}
        </p>
      )}
    </section>
  );
}
