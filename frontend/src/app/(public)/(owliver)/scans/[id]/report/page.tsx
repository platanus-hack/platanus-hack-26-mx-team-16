/**
 * `/scans/[id]/report` — Reporte "Owliver te explica" (§F7), el payoff. Light
 * mode. Two layers: the executive synthesis (big A–F grade + dual gauges + Opus
 * paragraph + top-3 risks + agentic inventory) and the technical accordion (one
 * panel per finding with evidence / impact / remediation / references). RSC by
 * default; the gauges, filters, accordion and share action are client islands.
 *
 * Data: `fetchReport` (server) → backend `GET /v1/scans/{id}/report`, with the
 * SAT demo fixture as offline fallback. 404 (private / missing) → notFound (the
 * backend never confirms existence).
 */
import { notFound } from "next/navigation";
import Link from "next/link";

import { fetchReport } from "@/src/application/owliver/lib/report-data";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { ReportExecutive } from "@/src/presentation/owliver/report/report-executive";
import { ReportTechnical } from "@/src/presentation/owliver/report/report-technical";
import { ReportActions } from "@/src/presentation/owliver/report/report-actions";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const report = await fetchReport(id);

  if (!report) {
    notFound();
  }

  const { scan } = report;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 md:px-6">
      {/* Header: target + level + actions */}
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-sm text-on-surface-variant">
            Reporte de seguridad
          </p>
          <h1 className="truncate text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
            {scan.host}
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            Nivel {scan.level} ·{" "}
            <Link
              href={`/scans/${scan.id}`}
              className="text-primary hover:underline"
            >
              ver escaneo en vivo
            </Link>
          </p>
        </div>
        <ReportActions scanId={scan.id} />
      </header>

      {/* Layer 1 — executive */}
      <ReportExecutive
        scan={scan}
        explanation={report.explanation}
        topRisks={report.topRisks}
        surfaces={report.surfaces}
      />

      <hr className="my-10 border-outline-variant" />

      {/* Layer 2 — technical */}
      <ReportTechnical findings={report.findings} />

      <div className="mt-10 flex justify-center">
        <Link
          href={`/sites/${scan.siteId}`}
          className={buttonVariants({ variant: "ghost", size: "sm" })}
        >
          Ver histórico del sitio →
        </Link>
      </div>
    </div>
  );
}
