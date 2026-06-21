/**
 * `/sites/[id]` — Site history (§F9). Public RSC, the click-destination from a
 * leaderboard row. Renders the latest scan summary (overall grade + the two
 * 🛡️/🤖 gauges), the detected agentic surface, the grade timeline + trend chart,
 * and a new-vs-resolved findings summary derived from consecutive history deltas
 * (first_seen / last_seen framing). Anonymous.
 *
 * Data: `backendGet("/sites/{id}")` server-side (BFF helper) with a fixture
 * fallback so the page renders without a backend. The frontend NEVER recomputes
 * grades/scores — it renders server values.
 */
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowRight, ArrowDownRight, ArrowUpRight, Bot, Landmark, Minus, Shield } from "lucide-react";

import { siteFixture } from "@/src/application/owliver/fixtures";
import { backendGet } from "@/src/application/owliver/lib/bff";
import { gradeLabel } from "@/src/application/owliver/lib/grade";
import type { Site } from "@/src/application/owliver/schemas/api";
import { siteSchema } from "@/src/application/owliver/schemas/api";
import { Gauge } from "@/src/presentation/owliver/components/gauge";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { CoverageBadges } from "@/src/presentation/owliver/components/status-badge";
import { GradeTrend } from "@/src/presentation/owliver/site/grade-trend";

export const dynamic = "force-dynamic";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

async function loadSite(id: string): Promise<Site | null> {
  const result = await backendGet<{ data?: unknown }>(`/sites/${id}`);
  if (result.ok) {
    const parsed = siteSchema.safeParse(
      (result.data as { data?: unknown })?.data ?? result.data
    );
    if (parsed.success) return parsed.data;
  }
  if (result.status === 404) return null;
  // Offline / dev: fixture fallback (matches the BFF route's behavior).
  return siteFixture;
}

/** Compare consecutive history score deltas → human "qué cambió" summary. */
function deriveChanges(history: Site["history"]) {
  if (history.length < 2) return null;
  const prev = history[history.length - 2];
  const curr = history[history.length - 1];
  const web = (curr.webScore ?? 0) - (prev.webScore ?? 0);
  const agentic = (curr.agenticScore ?? 0) - (prev.agenticScore ?? 0);
  return { web, agentic, prevGrade: prev.overallGrade, currGrade: curr.overallGrade };
}

function DeltaPill({ label, delta }: { label: string; delta: number }) {
  const improving = delta > 0; // higher score = better
  const flat = delta === 0;
  const Icon = flat ? Minus : improving ? ArrowUpRight : ArrowDownRight;
  const color = flat
    ? "var(--on-surface-variant)"
    : improving
      ? "var(--grade-a)"
      : "var(--grade-f)";
  return (
    <div className="flex items-center justify-between rounded-xl border border-outline-variant bg-card px-3 py-2.5">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span
        className="inline-flex items-center gap-1 font-mono text-sm font-semibold"
        style={{ color }}
      >
        <Icon className="size-4" aria-hidden />
        {delta > 0 ? "+" : ""}
        {delta} pts
      </span>
    </div>
  );
}

export default async function SiteHistoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const site = await loadSite(id);
  if (!site) notFound();

  const scan = site.latestScan;
  const changes = deriveChanges(site.history);
  const ordered = [...site.history].reverse(); // newest first for the timeline

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:px-6">
      {/* Header */}
      <header className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          {site.faviconUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={site.faviconUrl}
              alt=""
              width={48}
              height={48}
              className="mt-1 size-12 rounded-xl border border-outline-variant bg-card"
            />
          ) : null}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                {site.departmentName ?? site.host}
              </h1>
              {site.isGov && (
                <span className="inline-flex h-6 items-center gap-1 rounded-full border border-outline-variant bg-surface-container px-2 text-[11px] font-medium text-on-surface-variant">
                  <Landmark className="size-3" aria-hidden />
                  Sitio del Estado
                </span>
              )}
            </div>
            <p className="mt-1 font-mono text-sm text-on-surface-variant">
              {site.host}
            </p>
            {scan.finishedAt && (
              <p className="mt-1 text-xs text-on-surface-variant/80">
                Último escaneo: {formatDate(scan.finishedAt)}
              </p>
            )}
          </div>
        </div>

        {/* Current grade + report link */}
        <div className="flex shrink-0 items-center gap-4">
          {scan.overallGrade && (
            <div className="flex flex-col items-center">
              <GradeBadge grade={scan.overallGrade} size="lg" pulse />
              <span className="mt-1 text-xs text-on-surface-variant">
                {gradeLabel(scan.overallGrade)}
              </span>
            </div>
          )}
        </div>
      </header>

      <div className="mt-3">
        <CoverageBadges
          agenticStatus={scan.agenticStatus}
          partialCoverage={scan.partialCoverage}
        />
      </div>

      {/* Dual gauges */}
      <section className="mt-8 rounded-2xl border border-outline-variant bg-card p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-around gap-6">
          <Gauge
            score={scan.webScore}
            grade={scan.webGrade}
            label="Web"
            icon={<Shield className="size-4" aria-hidden />}
            emptyHint="sin datos"
          />
          <Gauge
            score={scan.agenticScore}
            grade={scan.agenticGrade}
            label="Agéntico"
            icon={<Bot className="size-4" aria-hidden />}
            emptyHint={
              scan.agenticStatus === "detected_not_tested"
                ? "sin auditar"
                : "sin superficie"
            }
          />
        </div>
        <div className="mt-5 flex justify-center">
          <Link
            href={`/scans/${scan.id}/report`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            Ver reporte completo
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </section>

      {/* Trend chart */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-foreground">
          Tendencia del grado
        </h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          {site.history.length} escaneos registrados.
        </p>
        <div className="mt-4 rounded-2xl border border-outline-variant bg-card p-4 shadow-xs">
          <GradeTrend history={site.history} />
        </div>
      </section>

      {/* New vs resolved (derived from consecutive deltas) */}
      {changes && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-foreground">
            Qué cambió desde el escaneo anterior
          </h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Grado {changes.prevGrade} → {changes.currGrade}. Comparación de
            sub-scores entre los dos últimos escaneos (vía first_seen /
            last_seen a nivel sitio).
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <DeltaPill label="🛡️ Web" delta={changes.web} />
            <DeltaPill label="🤖 Agéntico" delta={changes.agentic} />
          </div>
        </section>
      )}

      {/* Detected agentic surface */}
      {site.surfaces.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-foreground">
            Superficie agéntica detectada
          </h2>
          <ul className="mt-4 space-y-2">
            {site.surfaces.map((s) => (
              <li
                key={s.locationUrl}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-card px-4 py-3"
              >
                <Bot className="size-4 text-on-surface-variant" aria-hidden />
                <span className="font-medium text-foreground">
                  {s.vendor ?? "Asistente genérico"}
                </span>
                <span className="font-mono text-xs text-on-surface-variant">
                  {s.inferredModel ?? "modelo no expuesto"}
                </span>
                <CoverageBadges
                  agenticStatus={s.agenticStatus}
                  className="ml-auto"
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Scan timeline */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-foreground">
          Historial de escaneos
        </h2>
        <ol className="mt-4 space-y-2">
          {ordered.map((h) => (
            <li key={h.scanId}>
              <Link
                href={`/scans/${h.scanId}/report`}
                className="flex items-center gap-4 rounded-xl border border-outline-variant bg-card px-4 py-3 transition-colors hover:bg-surface-container-low"
              >
                <GradeBadge grade={h.overallGrade} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground">
                    {formatDate(h.scannedAt)}
                  </p>
                  <p className="font-mono text-xs text-on-surface-variant">
                    🛡️ {h.webScore ?? "—"} · 🤖 {h.agenticScore ?? "—"}
                  </p>
                </div>
                <ArrowRight
                  className="size-4 shrink-0 text-on-surface-variant"
                  aria-hidden
                />
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
