/**
 * ReportTechnical — Capa 2 wrapper (§F7/§F8). Client island: severity / source
 * / category filters over the finding accordion. `info` findings (weight 0) are
 * surfaced as a separate count and excluded from the scored list. Works for both
 * the full `Finding[]` and the redacted `RedactedFinding[]` (the accordion item
 * adapts via its `redacted` discriminant).
 */
"use client";

import * as React from "react";

import type {
  Finding,
  RedactedFinding,
  Severity,
  Source,
} from "@/src/application/owliver/schemas/api";
import { bySeverityDesc, severityLabel } from "@/src/application/owliver/lib/grade";
import { cn } from "@/src/application/lib/utils";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";
import { FindingAccordion } from "./finding-accordion";

type AnyFinding = Finding | RedactedFinding;

const SEVERITY_FILTERS: Severity[] = ["critical", "high", "medium", "low"];
const SOURCE_LABEL: Record<Source, React.ReactNode> = {
  owasp: (
    <span className="inline-flex items-center gap-1.5">
      <ShieldWeb className="size-3.5" /> Web
    </span>
  ),
  agentic: (
    <span className="inline-flex items-center gap-1.5">
      <AgenticChip className="size-3.5" /> Agéntico
    </span>
  ),
};

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-outline-variant bg-card text-on-surface-variant hover:bg-surface-container-low"
      )}
    >
      {children}
    </button>
  );
}

export type ReportTechnicalProps = {
  findings: AnyFinding[];
};

export function ReportTechnical({ findings }: ReportTechnicalProps) {
  const [severity, setSeverity] = React.useState<Severity | "all">("all");
  const [source, setSource] = React.useState<Source | "all">("all");

  const scored = React.useMemo(
    () => findings.filter((f) => f.severity !== "info"),
    [findings]
  );
  const infoFindings = React.useMemo(
    () => findings.filter((f) => f.severity === "info"),
    [findings]
  );

  const visible = React.useMemo(() => {
    return scored
      .filter((f) => (severity === "all" ? true : f.severity === severity))
      .filter((f) => (source === "all" ? true : f.source === source))
      .slice()
      .sort(bySeverityDesc);
  }, [scored, severity, source]);

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold text-foreground">
          Hallazgos técnicos
        </h2>
        <span className="font-mono text-sm text-on-surface-variant">
          {scored.length} hallazgos
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <FilterPill active={severity === "all"} onClick={() => setSeverity("all")}>
          Todas
        </FilterPill>
        {SEVERITY_FILTERS.map((s) => (
          <FilterPill
            key={s}
            active={severity === s}
            onClick={() => setSeverity(s)}
          >
            {severityLabel(s)}
          </FilterPill>
        ))}
        <span className="mx-1 h-8 w-px self-center bg-outline-variant" aria-hidden />
        <FilterPill active={source === "all"} onClick={() => setSource("all")}>
          Todo
        </FilterPill>
        {(["agentic", "owasp"] as Source[]).map((s) => (
          <FilterPill key={s} active={source === s} onClick={() => setSource(s)}>
            {SOURCE_LABEL[s]}
          </FilterPill>
        ))}
      </div>

      {visible.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-outline-variant bg-surface-container-low p-6 text-center text-sm text-on-surface-variant">
          No hay hallazgos con estos filtros.
        </p>
      ) : (
        <FindingAccordion findings={visible} />
      )}

      {infoFindings.length > 0 && (
        <p className="text-xs text-on-surface-variant">
          {infoFindings.length} nota(s) informativa(s) (peso 0, no afectan el
          puntaje) — incluyen avisos de cobertura.
        </p>
      )}
    </section>
  );
}
