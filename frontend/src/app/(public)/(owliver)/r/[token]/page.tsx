/**
 * `/r/[token]` — Reporte público redactado (§F8). Server Component, NO login.
 * The viral share surface: renders the FULL executive layer + redacted technical
 * findings — the raw exploit evidence (payloads, sqlmap requests, the leaked
 * system-prompt/canary) is stripped server-side and shown as a lock state. NEVER
 * renders raw evidence here.
 *
 * Token states (12-api contract): missing → 404 (notFound), expired/revoked →
 * 410 Gone ("Este enlace expiró"), valid → redacted report. `fetchPublicReport`
 * preserves the backend status; offline falls back to the redacted demo fixture.
 */
import { notFound } from "next/navigation";
import Link from "next/link";
import { Link2Off } from "lucide-react";

import { fetchPublicReport } from "@/src/application/owliver/lib/report-data";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { OwlMark } from "@/src/presentation/owliver/icons";
import { ReportExecutive } from "@/src/presentation/owliver/report/report-executive";
import { ReportTechnical } from "@/src/presentation/owliver/report/report-technical";

function ExpiredState() {
  return (
    <div className="mx-auto max-w-md px-4 py-24 text-center">
      <Link2Off
        className="mx-auto mb-4 size-12 text-on-surface-variant"
        aria-hidden
      />
      <h1 className="text-2xl font-semibold text-foreground">
        Este enlace expiró
      </h1>
      <p className="mt-2 text-sm text-on-surface-variant">
        El reporte público que buscas ya no está disponible. Los enlaces
        compartidos caducan a los 7 días.
      </p>
      <Link
        href="/"
        className={`mt-6 ${buttonVariants({ variant: "tertiary", size: "lg" })}`}
      >
        Ir al Hall of Shame →
      </Link>
    </div>
  );
}

export default async function PublicReportPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const result = await fetchPublicReport(token);

  if (result.status === "not_found") {
    notFound();
  }
  if (result.status === "gone") {
    return <ExpiredState />;
  }

  const { report } = result;
  const { scan } = report;
  const title = report.departmentName ?? scan.host;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 md:px-6">
      <header className="mb-8">
        <p className="inline-flex items-center gap-1.5 font-mono text-sm text-on-surface-variant">
          Reporte público · Owliver
          <OwlMark className="size-4" />
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
          {title}
        </h1>
        <p className="mt-1 truncate font-mono text-sm text-on-surface-variant">
          {scan.host}
        </p>
      </header>

      {/* Layer 1 — full executive layer (safe to share) */}
      <ReportExecutive
        scan={scan}
        explanation={report.explanation}
        topRisks={report.topRisks}
        surfaces={report.surfaces}
        departmentName={report.departmentName}
      />

      <hr className="my-10 border-outline-variant" />

      {/* Layer 2 — redacted technical layer (exploits hidden) */}
      <ReportTechnical findings={report.findings} />

      <p className="mt-10 text-center text-xs text-on-surface-variant">
        Reporte generado por Owliver — la evidencia de explotación se oculta en
        los enlaces públicos.
      </p>
    </div>
  );
}
