"use client";

/**
 * Renders the analysis-run experience for a case. State is owned by
 * `useAnalysisRuns` (lifted to WorkflowCaseDetailView) so the bottom
 * pane and the main tab stay in sync.
 */

import { AlertCircle, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import type { UseAnalysisRunsResult } from "src/application/hooks/use-analysis-runs";
import type { AnalysisRuleResult } from "src/domain/entities/analysis-run";
import { EmptyState } from "src/presentation/components/common/empty-state";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "src/presentation/components/ui/alert";
import { RunSummarySection } from "src/presentation/workflows/run-summary/run-summary-section";
import { AnalysisRuleResultsCard } from "../cards/analysis-rule-results";
import { AnalysisRunningState } from "../cards/analysis-running-state";

interface Props {
  runs: UseAnalysisRunsResult;
  paneOpen?: boolean;
  expandedIds: Set<string>;
  onToggleRow: (uuid: string) => void;
}

export function WorkflowAnalysisTab({
  runs,
  paneOpen = false,
  expandedIds,
  onToggleRow,
}: Props) {
  const grouped = groupByRule(runs.results);
  const showEmptyState =
    runs.isHydrated && runs.history.length === 0 && !runs.error;

  if (showEmptyState) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="Sin resultados todavía"
        description="Ejecuta un análisis para evaluar las reglas activas contra los documentos extraídos del case."
      />
    );
  }

  const isCanceling = runs.activeRun?.status === "CANCELING";
  if (runs.isLive && runs.results.length === 0) {
    return (
      <AnalysisRunningState
        completed={runs.completedEvaluations}
        total={runs.totalEvaluations}
        isCanceling={isCanceling}
        paneOpen={paneOpen}
      />
    );
  }

  const summaryRunId =
    runs.activeRun?.status === "COMPLETED"
      ? runs.activeRun.uuid
      : runs.history.find((r) => r.status === "COMPLETED")?.uuid ?? null;
  const ruleNamesById = useMemo(
    () =>
      Object.fromEntries(
        runs.results
          .filter((r) => r.ruleName)
          .map((r) => [r.ruleId, r.ruleName as string])
      ),
    [runs.results]
  );

  return (
    <div className="space-y-4">
      {runs.error ? (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertTitle>No pudimos iniciar el análisis</AlertTitle>
          <AlertDescription>{runs.error}</AlertDescription>
        </Alert>
      ) : null}

      <RunSummarySection runId={summaryRunId} ruleNamesById={ruleNamesById} />

      {grouped.length > 0 ? (
        <div className="space-y-3">
          {grouped.map(({ ruleId, ruleName, results }) => (
            <AnalysisRuleResultsCard
              key={ruleId}
              ruleId={ruleId}
              ruleName={ruleName}
              results={results}
              expandedIds={expandedIds}
              onToggleRow={onToggleRow}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function groupByRule(results: AnalysisRuleResult[]) {
  const map = new Map<
    string,
    { ruleId: string; ruleName: string | null; results: AnalysisRuleResult[] }
  >();
  for (const r of results) {
    if (!map.has(r.ruleId)) {
      map.set(r.ruleId, {
        ruleId: r.ruleId,
        ruleName: r.ruleName,
        results: [],
      });
    }
    map.get(r.ruleId)!.results.push(r);
  }
  return Array.from(map.values());
}
