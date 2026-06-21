/**
 * ReportExecutive — Capa 1 "Owliver te explica" (§F7 / §F8). The executive
 * layer shared by the full report (`/scans/[id]/report`) and the redacted public
 * report (`/r/[token]`): the big A–F grade (count-up), the two semicircular
 * Gauges (🛡️ Web / 🤖 Agéntico), the plain-language Opus synthesis paragraph,
 * the top-3 prioritized risks, the detected agentic-surface inventory, and the
 * coverage/agentic status badges. RSC-safe except for the animated Gauge/CountUp
 * (client islands) which already honor reduced-motion.
 *
 * The frontend NEVER computes the grade/score — it renders server values
 * (overallGrade / webScore / agenticScore / webGrade / agenticGrade).
 */
import type { AgenticSurface, Scan } from "@/src/application/owliver/schemas/api";
import { gradeColorVar, gradeLabel } from "@/src/application/owliver/lib/grade";
import { CountUp } from "@/src/presentation/components/common/count-up";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { Gauge } from "@/src/presentation/owliver/components/gauge";
import { CoverageBadges } from "@/src/presentation/owliver/components/status-badge";
import {
  AgenticChip,
  OwlMark,
  ShieldWeb,
} from "@/src/presentation/owliver/icons";

export type ReportExecutiveProps = {
  scan: Scan;
  explanation: string;
  topRisks: { title: string; impact: string }[];
  surfaces: AgenticSurface[];
  /** Department / site display name (public report card framing). */
  departmentName?: string | null;
};

export function ReportExecutive({
  scan,
  explanation,
  topRisks,
  surfaces,
  departmentName,
}: ReportExecutiveProps) {
  const grade = scan.overallGrade;

  return (
    <section className="space-y-8">
      {/* Grade + dual gauges hero */}
      <div className="grid items-center gap-8 rounded-3xl border border-outline-variant bg-card p-6 shadow-xs md:grid-cols-[auto_1fr] md:p-8">
        <div className="flex flex-col items-center gap-3 text-center">
          {grade ? (
            <>
              <GradeBadge grade={grade} size="xl" pulse={grade === "F"} />
              <div
                className="font-mono text-sm font-medium"
                style={{ color: gradeColorVar(grade) }}
              >
                {gradeLabel(grade)}
              </div>
            </>
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-3xl border border-dashed border-outline-variant font-mono text-2xl text-on-surface-variant">
              —
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-6 md:justify-end">
          <Gauge
            score={scan.webScore}
            grade={scan.webGrade}
            label="Web"
            icon={<ShieldWeb className="size-4 text-primary" />}
            emptyHint="sin datos"
          />
          <Gauge
            score={scan.agenticScore}
            grade={scan.agenticGrade}
            label="Agéntico"
            icon={<AgenticChip className="size-4 text-tertiary" />}
            emptyHint={
              scan.agenticStatus === "detected_not_tested"
                ? "sin auditar"
                : "sin IA"
            }
          />
        </div>
      </div>

      {/* Status badges */}
      <CoverageBadges
        agenticStatus={scan.agenticStatus ?? "no_surface"}
        partialCoverage={scan.partialCoverage}
      />

      {/* "Owliver te explica" synthesis */}
      <Reveal className="rounded-2xl border border-outline-variant bg-surface-container-low p-5 md:p-6">
        <div className="mb-2 flex items-center gap-2">
          <OwlMark className="size-5 text-primary" />
          <h2 className="text-base font-semibold text-foreground">
            Owliver te explica
          </h2>
        </div>
        <p className="text-[15px] leading-relaxed text-on-surface-variant">
          {explanation}
        </p>
      </Reveal>

      {/* Top 3 risks */}
      {topRisks.length > 0 && (
        <div>
          <h2 className="mb-3 text-base font-semibold text-foreground">
            Principales riesgos
          </h2>
          <ol className="space-y-3">
            {topRisks.slice(0, 3).map((risk, i) => (
              <li
                key={risk.title}
                className="flex gap-3 rounded-2xl border border-outline-variant bg-card p-4 shadow-xs"
              >
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-tertiary-container font-mono text-xs font-semibold text-on-tertiary-container">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-medium text-foreground">{risk.title}</p>
                  <p className="mt-0.5 text-sm text-on-surface-variant">
                    {risk.impact}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Agentic surface inventory */}
      <div>
        <h2 className="mb-3 text-base font-semibold text-foreground">
          Superficie agéntica detectada
        </h2>
        {surfaces.length === 0 ? (
          <p className="text-sm text-on-surface-variant">
            No se detectaron chatbots ni widgets de IA en este sitio.
          </p>
        ) : (
          <ul className="space-y-2">
            {surfaces.map((s) => (
              <li
                key={s.locationUrl}
                className="flex flex-wrap items-center gap-3 rounded-2xl border border-outline-variant bg-card p-4 shadow-xs"
              >
                <AgenticChip className="size-5 text-tertiary" />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-foreground">
                    {s.vendor ?? "Chatbot"} · {s.type}
                  </p>
                  <p className="truncate font-mono text-xs text-on-surface-variant">
                    {s.locationUrl}
                  </p>
                </div>
                <span className="font-mono text-xs text-on-surface-variant">
                  {s.inferredModel ?? "modelo no expuesto"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Department name (used by the public report card framing) */}
      {departmentName ? (
        <p className="sr-only">{departmentName}</p>
      ) : null}

      {/* Animated score line (count-up) only when scores exist. */}
      {typeof scan.webScore === "number" && (
        <p className="font-mono text-xs text-on-surface-variant">
          <span>Puntaje web </span>
          <CountUp
            to={scan.webScore}
            className="font-semibold text-foreground"
          />
          {typeof scan.agenticScore === "number" && (
            <>
              <span> · puntaje agéntico </span>
              <CountUp
                to={scan.agenticScore}
                className="font-semibold text-foreground"
              />
            </>
          )}
        </p>
      )}
    </section>
  );
}
