"use client";

import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "src/application/lib/utils";
import type {
  AnalysisRuleResult,
  Citation,
} from "src/domain/entities/analysis-run";
import { classifyConfidence } from "src/domain/entities/analysis-run";
import { ShortId } from "src/presentation/components/common/short-id";

interface Props {
  ruleId: string;
  ruleName: string | null;
  results: AnalysisRuleResult[];
  expandedIds: Set<string>;
  onToggleRow: (uuid: string) => void;
}

export function AnalysisRuleResultsCard({
  ruleId,
  ruleName,
  results,
  expandedIds,
  onToggleRow,
}: Props) {
  const passed = results.filter((r) => r.isPassed === true).length;
  const failed = results.filter((r) => r.isPassed === false).length;
  const errored = results.filter((r) => r.error || r.isPassed === null).length;

  return (
    <section className="overflow-hidden rounded-md border bg-card">
      <header className="flex items-center justify-between gap-4 border-b border-border/60 bg-muted/30 px-4 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <ShortId value={ruleId} />
          <h3 className="truncate text-sm font-medium leading-tight text-foreground">
            {ruleName ?? "Regla"}
          </h3>
        </div>
        <AnalysisRuleStats
          passed={passed}
          failed={failed}
          errored={errored}
          total={results.length}
        />
      </header>
      <ul className="divide-y divide-border/50">
        {results.map((result) => (
          <li key={result.uuid}>
            <AnalysisResultRow
              result={result}
              expanded={expandedIds.has(result.uuid)}
              onToggle={() => onToggleRow(result.uuid)}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

export function isExpandableResult(result: AnalysisRuleResult): boolean {
  return hasDetails(result);
}

function AnalysisRuleStats({
  passed,
  failed,
  errored,
  total,
}: {
  passed: number;
  failed: number;
  errored: number;
  total: number;
}) {
  return (
    <div className="flex shrink-0 items-baseline gap-2.5 font-mono text-[10px] uppercase tracking-[0.14em]">
      {passed > 0 ? (
        <span className="text-emerald-700 dark:text-emerald-400">
          {passed} ok
        </span>
      ) : null}
      {failed > 0 ? (
        <span className="text-red-700 dark:text-red-400">{failed} fail</span>
      ) : null}
      {errored > 0 ? (
        <span className="text-amber-700 dark:text-amber-400">
          {errored} err
        </span>
      ) : null}
      <span className="text-muted-foreground/70">/ {total}</span>
    </div>
  );
}

enum Verdict {
  Passed = "passed",
  Failed = "failed",
  Inconclusive = "inconclusive",
}

const VERDICT_BAR: Record<Verdict, string> = {
  [Verdict.Passed]: "bg-emerald-500",
  [Verdict.Failed]: "bg-red-500",
  [Verdict.Inconclusive]: "bg-amber-500",
};

const VERDICT_LABEL: Record<Verdict, string> = {
  [Verdict.Passed]: "ok",
  [Verdict.Failed]: "fail",
  [Verdict.Inconclusive]: "?",
};

const VERDICT_TONE: Record<Verdict, string> = {
  [Verdict.Passed]: "text-emerald-700 dark:text-emerald-400",
  [Verdict.Failed]: "text-red-700 dark:text-red-400",
  [Verdict.Inconclusive]: "text-amber-700 dark:text-amber-400",
};

// Slug fallback for refs whose backing doctype was renamed away or never
// resolved by the endpoint — we still want to show *something* legible
// rather than a raw `comprobante_de_domicilio`.
function formatDoctypeSlug(slug: string): string {
  return slug.replace(/[_-]+/g, " ").trim();
}

function getVerdict(result: AnalysisRuleResult): Verdict {
  if (result.isPassed === true) return Verdict.Passed;
  if (result.isPassed === false) return Verdict.Failed;
  return Verdict.Inconclusive;
}

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={cn(
        "shrink-0 font-mono text-[10px] uppercase tracking-[0.18em]",
        VERDICT_TONE[verdict]
      )}
    >
      {VERDICT_LABEL[verdict]}
    </span>
  );
}

function hasDetails(result: AnalysisRuleResult): boolean {
  return Boolean(
    result.reasoning ||
      result.error ||
      (result.citations?.length ?? 0) > 0 ||
      result.criticFeedback ||
      (result.verificationWarnings?.length ?? 0) > 0 ||
      result.structuredOutput
  );
}

function AnalysisResultRow({
  result,
  expanded,
  onToggle,
}: {
  result: AnalysisRuleResult;
  expanded: boolean;
  onToggle: () => void;
}) {
  const verdict = getVerdict(result);

  const refsLabel = Object.entries(result.documentRefs ?? {})
    .map(([slug, ref]) => {
      const label = ref.documentTypeName ?? formatDoctypeSlug(slug);
      return ref.documentId ? label : `${label}*`;
    })
    .join(", ");

  const expandable = hasDetails(result);

  return (
    <div className="relative">
      <span
        aria-hidden
        className={`absolute inset-y-0 left-0 w-0.75 ${VERDICT_BAR[verdict]}`}
      />
      <button
        type="button"
        onClick={() => expandable && onToggle()}
        disabled={!expandable}
        aria-expanded={expandable ? expanded : undefined}
        className="flex w-full cursor-pointer items-center gap-3 py-2 pl-4 pr-3 text-left transition-colors hover:bg-muted/50 disabled:cursor-default disabled:hover:bg-transparent"
      >
        <VerdictBadge verdict={verdict} />
        <ShortId value={result.uuid} />
        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {refsLabel || "sin documentos"}
        </span>
        <ConfidenceTag result={result} />
        {expandable ? (
          <ChevronRight
            className={`size-3.5 shrink-0 text-muted-foreground/60 transition-transform ${
              expanded ? "rotate-90" : ""
            }`}
          />
        ) : null}
      </button>
      {expanded && expandable ? (
        <div className="space-y-3 bg-muted/15 pb-3 pl-4 pr-4 pt-1">
          {result.error ? (
            <Section label="Error" tone="error">
              <p className="text-xs leading-relaxed text-muted-foreground">
                {result.error}
              </p>
            </Section>
          ) : null}
          {result.reasoning ? (
            <Section label="Razonamiento">
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                {result.reasoning}
              </p>
            </Section>
          ) : null}
          {(result.citations?.length ?? 0) > 0 ? (
            <Section label={`Citaciones · ${result.citations.length}`}>
              <CitationsList citations={result.citations} />
            </Section>
          ) : null}
          {result.criticFeedback ? (
            <Section label="Crítico" tone="critic">
              <p className="text-xs leading-relaxed text-muted-foreground">
                {result.criticFeedback}
              </p>
            </Section>
          ) : null}
          {(result.verificationWarnings?.length ?? 0) > 0 ? (
            <Section
              label={`Advertencias · ${result.verificationWarnings.length}`}
              tone="warning"
            >
              <ul className="space-y-0.5 text-xs leading-relaxed text-muted-foreground">
                {result.verificationWarnings.map((w, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-amber-700/70 dark:text-amber-400/70">
                      ›
                    </span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}
          {result.structuredOutput ? (
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/70 transition-colors hover:text-muted-foreground">
                <ChevronRight className="size-3 transition-transform group-open:rotate-90" />
                Output técnico
              </summary>
              <pre className="mt-2 overflow-x-auto rounded border border-border/40 bg-background/60 p-2 text-[10px] leading-relaxed text-foreground/75">
                {JSON.stringify(result.structuredOutput, null, 2)}
              </pre>
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

type SectionTone = "default" | "error" | "warning" | "critic";

const SECTION_LABEL_TONE: Record<SectionTone, string> = {
  default: "text-foreground/80",
  error: "text-red-700 dark:text-red-400",
  warning: "text-amber-700 dark:text-amber-400",
  critic: "text-violet-700 dark:text-violet-400",
};

function Section({
  label,
  tone = "default",
  children,
}: {
  label: string;
  tone?: SectionTone;
  children: ReactNode;
}) {
  return (
    <div>
      <div
        className={`mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] ${SECTION_LABEL_TONE[tone]}`}
      >
        {label}
      </div>
      <div>{children}</div>
    </div>
  );
}

function CitationsList({ citations }: { citations: Citation[] }) {
  return (
    <ul className="space-y-0.5">
      {citations.map((cit, idx) => (
        <li key={idx} className="text-xs leading-relaxed text-muted-foreground">
          <span className="font-mono text-foreground/70">
            {cit.documentTypeSlug
              ? `@${cit.documentTypeSlug}${cit.fieldPath ? `.${cit.fieldPath}` : ""}`
              : (cit.fieldPath ?? "")}
          </span>
          {cit.value !== null && cit.value !== undefined ? (
            <span> · {String(cit.value)}</span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

const CONFIDENCE_TONE: Record<string, string> = {
  high: "text-emerald-700 dark:text-emerald-400",
  medium: "text-amber-700 dark:text-amber-400",
  critic_reviewed: "text-violet-700 dark:text-violet-400",
  inconclusive: "text-muted-foreground",
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: "alta",
  medium: "media",
  critic_reviewed: "crítico",
  inconclusive: "inconclusa",
};

function ConfidenceTag({ result }: { result: AnalysisRuleResult }) {
  const level = classifyConfidence(result);
  if (!level || !CONFIDENCE_LABEL[level]) return null;
  return (
    <span
      className={`shrink-0 font-mono text-[10px] uppercase tracking-[0.16em] ${CONFIDENCE_TONE[level] ?? "text-muted-foreground"}`}
    >
      {CONFIDENCE_LABEL[level]}
    </span>
  );
}
