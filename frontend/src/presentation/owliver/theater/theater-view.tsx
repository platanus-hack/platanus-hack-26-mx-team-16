/**
 * TheaterView — the ★ Live Pentest Theater (§F6, the centerpiece). A "use client"
 * war-room that consumes `useScanStream` (SSE replay-then-tail) into the theater
 * store and paints the live pentest: two agent lanes (🛡️ OWASP / 🤖 Agentic) with
 * tool chips igniting/finishing, a live findings feed, animated partial gauges, a
 * progress bar with the current phase + a reassuring <90s timer, and a scrolling
 * monospace telemetry log.
 *
 * Everything is scoped to the dark SOC palette via the `.soc` wrapper. On the
 * terminal `done` event a big "Ver reporte completo →" CTA appears; Cancelar fires
 * `POST /cancel` (→ terminal `done {cancelled}`). Reload is idempotent: the store
 * discards `seq <= lastSeq`, so the backend replay repaints the whole run.
 */
"use client";

import * as React from "react";
import Link from "next/link";
import { Ban, FileText, Loader2, Radio } from "lucide-react";

import { cn } from "@/src/application/lib/utils";
import { useScanStream } from "@/src/application/owliver/hooks/use-scan-stream";
import { useCancelScan } from "@/src/application/owliver/hooks/use-scan";
import {
  isTerminal,
  useTheaterStore,
} from "@/src/application/owliver/stores/theater-store";
import type { Scan } from "@/src/application/owliver/schemas/api";
import {
  Button,
  buttonVariants,
} from "@/src/presentation/components/ui/button";
import {
  AgentLane,
  Gauge,
  GradeBadge,
  OwlMascot,
  ProgressBar,
  FindingFeedItem,
} from "@/src/presentation/owliver";

export type TheaterViewProps = {
  scanId: string;
  /** Initial server state (seeds the header before the first SSE frame). */
  initialScan: Scan;
  /** Ephemeral token for private scans (?stream_token=). */
  streamToken?: string;
};

const LEVEL_LABEL: Record<string, string> = {
  basico: "Básico · pasivo",
  intermedio: "Intermedio · activo suave",
  avanzado: "Avanzado · explotación",
};

/**
 * Telemetry event-type → SOC functional-neon color (same token vocabulary as
 * ToolChip): each hue reports a real state, never decoration. coral = a hit,
 * amber = a tool firing, green = done/ok, cyan = activity, muted = a phase note.
 */
const LOG_TYPE_COLOR: Record<string, string> = {
  finding: "var(--destructive)",
  error: "var(--destructive)",
  tool_start: "var(--tertiary)",
  tool_end: "var(--success)",
  done: "var(--success)",
  score: "var(--primary)",
  agent_status: "var(--primary)",
  phase: "var(--muted-foreground)",
};

/** Elapsed seconds since `startedAt`, ticking once a second while running. */
function useElapsed(startedAt: string | null | undefined, running: boolean) {
  const start = React.useMemo(
    () => (startedAt ? new Date(startedAt).getTime() : Date.now()),
    [startedAt]
  );
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running]);
  return Math.max(0, Math.floor((now - start) / 1000));
}

export function TheaterView({
  scanId,
  initialScan,
  streamToken,
}: TheaterViewProps) {
  // Open the SSE stream through our dedicated BFF proxy (replay-then-tail).
  const { connection } = useScanStream(scanId, {
    streamToken,
    basePath: "/api/owliver/scans",
  });

  // Subscribe to store slices (each is a stable selector → minimal re-renders).
  const runStatus = useTheaterStore((s) => s.runStatus);
  const progress = useTheaterStore((s) => s.progress);
  const currentPhase = useTheaterStore((s) => s.currentPhase);
  const webScore = useTheaterStore((s) => s.webScore);
  const agenticScore = useTheaterStore((s) => s.agenticScore);
  const lanes = useTheaterStore((s) => s.lanes);
  const findings = useTheaterStore((s) => s.findings);
  const log = useTheaterStore((s) => s.log);
  const terminalMessage = useTheaterStore((s) => s.terminalMessage);

  const cancel = useCancelScan(scanId);

  const terminal = isTerminal(runStatus);
  const running = !terminal && initialScan.status !== "queued";
  const elapsed = useElapsed(initialScan.startedAt, running);

  // Prefer live store values; fall back to the seeded server state.
  const phase = currentPhase ?? initialScan.currentPhase ?? null;
  const liveProgress = progress || initialScan.progress || 0;
  const liveWeb = webScore ?? initialScan.webScore ?? null;
  const liveAgentic = agenticScore ?? initialScan.agenticScore ?? null;

  // Auto-scroll the telemetry log to the newest line.
  const logRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log.length]);

  // Newest finding first in the feed (most recent hit on top).
  const feed = React.useMemo(() => [...findings].reverse(), [findings]);

  const queued = initialScan.status === "queued" && runStatus === "idle";
  const cancelled = runStatus === "cancelled";
  const errored = runStatus === "error";

  return (
    <div className="soc fixed inset-0 z-50 overflow-y-auto bg-background text-foreground">
      {/* Subtle scanline / grid backdrop — functional neon, not decoration. */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, var(--ring) 0, var(--ring) 1px, transparent 1px, transparent 4px)",
        }}
      />

      <div className="relative mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* ─── Header: target + level + grade-in-construction + progress ─── */}
        <header className="mb-6 rounded-2xl border border-outline-variant bg-surface-container-low p-4 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <OwlMascot state={terminal ? "idle" : "running"} size={48} />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Radio
                    className={cn(
                      "size-3.5",
                      connection === "open" && !terminal
                        ? "text-primary motion-safe:animate-pulse"
                        : "text-muted-foreground"
                    )}
                    aria-hidden
                  />
                  <span className="font-mono text-xs uppercase tracking-wide text-on-surface-variant">
                    {terminal
                      ? "transmisión finalizada"
                      : connection === "open"
                        ? "en vivo"
                        : "conectando…"}
                  </span>
                </div>
                <h1 className="font-mono text-xl font-semibold text-foreground md:text-2xl">
                  {initialScan.host}
                </h1>
                <p className="text-xs text-on-surface-variant">
                  {LEVEL_LABEL[initialScan.level] ?? initialScan.level}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Grade-in-construction: placeholder until the run is terminal. */}
              {initialScan.overallGrade && terminal ? (
                <GradeBadge grade={initialScan.overallGrade} size="lg" />
              ) : (
                <div
                  className="flex size-14 items-center justify-center rounded-xl border border-dashed border-outline-variant font-mono text-2xl font-bold text-muted-foreground"
                  aria-label="Grado en construcción"
                  title="Grado en construcción"
                >
                  ?
                </div>
              )}
              {terminal ? (
                <Link
                  href={`/scans/${scanId}/report`}
                  className={buttonVariants({
                    variant: "tertiary",
                    size: "lg",
                  })}
                >
                  <FileText className="size-4" />
                  Ver reporte completo
                  <span aria-hidden>→</span>
                </Link>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => cancel.mutate()}
                  disabled={cancel.isPending}
                >
                  {cancel.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Ban className="size-4" />
                  )}
                  Cancelar
                </Button>
              )}
            </div>
          </div>

          <div className="mt-5">
            <ProgressBar
              value={liveProgress}
              phase={
                terminal
                  ? (terminalMessage ?? "Escaneo completo")
                  : (phase ?? "Preparando…")
              }
              elapsedSeconds={terminal ? null : elapsed}
              budgetSeconds={90}
            />
          </div>

          {/* Terminal banners (partial / cancelled / error). */}
          {initialScan.partialCoverage && terminal && (
            <p className="mt-3 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning-deep">
              Cobertura parcial — algún scanner no completó; el grado queda capado
              en C.
            </p>
          )}
          {cancelled && (
            <p className="mt-3 rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
              Escaneo cancelado.
            </p>
          )}
          {errored && (
            <p className="mt-3 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive-deep">
              {terminalMessage ?? initialScan.error ?? "El escaneo falló."}
            </p>
          )}
        </header>

        {queued ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-outline-variant bg-surface-container-low py-16 text-center">
            <OwlMascot state="idle" size={64} />
            <p className="font-mono text-sm text-on-surface-variant">
              En cola — el búho está dormido, esperando turno…
            </p>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1.1fr]">
            {/* ─── Lane: OWASP Scanner ─── */}
            <AgentLane
              lane={lanes.owasp}
              title="OWASP Scanner"
              icon="🛡️"
              runStatus={runStatus}
            />
            {/* ─── Lane: Agentic Surface Auditor ─── */}
            <AgentLane
              lane={lanes.agentic}
              title="Agentic Surface Auditor"
              icon="🤖"
              runStatus={runStatus}
            />

            {/* ─── Live findings feed ─── */}
            <section className="flex flex-col gap-3 rounded-2xl border border-outline-variant bg-surface-container-low p-4 lg:row-span-2">
              <header className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground">
                  Hallazgos en vivo
                </h2>
                <span className="font-mono text-xs text-on-surface-variant">
                  {findings.length}
                </span>
              </header>
              <div className="flex flex-col gap-2">
                {feed.length === 0 ? (
                  <p className="py-8 text-center text-xs text-on-surface-variant">
                    Aún sin hallazgos. El búho sigue cazando…
                  </p>
                ) : (
                  feed.map((f) => (
                    <FindingFeedItem
                      key={f.key}
                      severity={f.severity}
                      title={f.title}
                      category={f.category}
                      source={f.source}
                      live
                    />
                  ))
                )}
              </div>
            </section>

            {/* ─── Partial scores (telemetry) ─── */}
            <section className="flex items-center justify-around gap-4 rounded-2xl border border-outline-variant bg-surface-container-low p-4 lg:col-span-2">
              <Gauge
                score={liveWeb}
                grade={terminal ? initialScan.webGrade : null}
                label="Web"
                icon={<span aria-hidden>🛡️</span>}
                size={132}
                emptyHint="midiendo…"
              />
              <Gauge
                score={liveAgentic}
                grade={terminal ? initialScan.agenticGrade : null}
                label="Agéntico"
                icon={<span aria-hidden>🤖</span>}
                size={132}
                emptyHint="midiendo…"
              />
            </section>

            {/* ─── Monospace terminal log ─── */}
            <section className="rounded-2xl border border-outline-variant bg-surface-container-lowest p-3 lg:col-span-3">
              <div className="mb-2 flex items-center gap-2">
                <span className="size-2 rounded-full bg-primary" aria-hidden />
                <span className="font-mono text-xs uppercase tracking-wide text-on-surface-variant">
                  telemetría
                </span>
              </div>
              <div
                ref={logRef}
                className="max-h-48 overflow-y-auto font-mono text-[12px] leading-relaxed"
                role="log"
                aria-live="polite"
                aria-label="Registro de telemetría del escaneo"
              >
                {log.length === 0 ? (
                  <p className="text-muted-foreground">
                    Esperando eventos del stream…
                  </p>
                ) : (
                  log.map((l) => (
                    <div key={l.seq} className="flex gap-2">
                      <span className="shrink-0 text-muted-foreground tabular-nums">
                        {new Date(l.ts).toLocaleTimeString("es-MX", {
                          hour12: false,
                        })}
                      </span>
                      <span
                        className="shrink-0 font-semibold"
                        style={{
                          color:
                            LOG_TYPE_COLOR[l.type] ?? "var(--on-surface-variant)",
                        }}
                      >
                        {l.type.padEnd(12, " ")}
                      </span>
                      <span className="text-on-surface-variant">{l.message}</span>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
