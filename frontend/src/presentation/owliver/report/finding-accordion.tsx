/**
 * FindingAccordion — Capa 2 técnica del reporte (§F7 / §F8). One collapsible
 * panel per finding built on the existing Base UI `Collapsible` (no new dep):
 * header = SeverityChip + category + title; body = evidence (payload / req /
 * resp / screenshot / canary), impact, remediation, references, confidence.
 *
 * Two render modes via the `redacted` discriminant:
 *  - full (`/scans/[id]/report`) → shows the raw evidence block. The STAR
 *    agentic finding's leaked canary token is highlighted as incontestable proof.
 *  - redacted (`/r/[token]`) → the exploit block is replaced by a lock state
 *    ("Oculto en el reporte público"). NEVER renders raw evidence.
 */
"use client";

import type * as React from "react";
import { ChevronDown, Lock, ShieldAlert } from "lucide-react";

import type {
  Finding,
  RedactedFinding,
} from "@/src/application/owliver/schemas/api";
import { cn } from "@/src/application/lib/utils";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/src/presentation/components/ui/collapsible";
import { SeverityChip } from "@/src/presentation/owliver/components/severity-chip";

type AnyFinding = Finding | RedactedFinding;

function isRedacted(f: AnyFinding): f is RedactedFinding {
  return (f as RedactedFinding).redacted !== undefined;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
        {label}
      </h4>
      <div className="text-sm leading-relaxed text-foreground">{children}</div>
    </div>
  );
}

function MonoBlock({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <pre
      className={cn(
        "max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-outline-variant bg-surface-container p-3 font-mono text-xs leading-relaxed text-on-surface-variant",
        className
      )}
    >
      {children}
    </pre>
  );
}

function EvidenceBlock({ finding }: { finding: Finding }) {
  const ev = finding.evidence ?? {};
  const star = ev.canary != null;
  return (
    <div className="space-y-3">
      {star && (
        <div
          className="rounded-xl border-2 p-3"
          style={{
            borderColor: "color-mix(in oklab, var(--grade-f) 50%, transparent)",
            backgroundColor: "color-mix(in oklab, var(--grade-f) 8%, transparent)",
          }}
        >
          <div className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-destructive">
            <ShieldAlert className="size-4" aria-hidden />
            Token canario filtrado — prueba incontestable
          </div>
          <p
            className="font-mono text-base font-bold tracking-tight text-destructive-deep"
            data-testid="canary"
          >
            {ev.canary}
          </p>
          {ev.reason && (
            <p className="mt-1 text-xs text-on-surface-variant">{ev.reason}</p>
          )}
        </div>
      )}
      {ev.payload && (
        <Field label="Payload">
          <MonoBlock>{ev.payload}</MonoBlock>
        </Field>
      )}
      {ev.request && (
        <Field label="Solicitud">
          <MonoBlock>{ev.request}</MonoBlock>
        </Field>
      )}
      {ev.response && (
        <Field label="Respuesta">
          <MonoBlock>{ev.response}</MonoBlock>
        </Field>
      )}
      {ev.screenshot && (
        // Static FastAPI route (/static/scans/{scan_id}/{file}); not a Next-optimizable asset.
        // biome-ignore lint/performance/noImgElement: served from FastAPI static route.
        <img
          src={ev.screenshot}
          alt="Captura de evidencia"
          className="max-h-80 rounded-lg border border-outline-variant bg-surface-container object-contain"
        />
      )}
    </div>
  );
}

function RedactedEvidence() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-dashed border-outline-variant bg-surface-container px-4 py-3 text-on-surface-variant">
      <Lock className="size-4 shrink-0" aria-hidden />
      <span className="text-sm">
        Evidencia de explotación{" "}
        <span className="font-medium">oculta en el reporte público</span>.
      </span>
    </div>
  );
}

export type FindingAccordionItemProps = {
  finding: AnyFinding;
  defaultOpen?: boolean;
};

export function FindingAccordionItem({
  finding,
  defaultOpen = false,
}: FindingAccordionItemProps) {
  const redacted = isRedacted(finding);
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      className="rounded-2xl border border-outline-variant bg-card shadow-xs"
    >
      <CollapsibleTrigger
        render={
          <button
            type="button"
            className="group flex w-full items-start gap-3 p-4 text-left"
          />
        }
      >
        <SeverityChip
          severity={finding.severity}
          iconOnly
          size="sm"
          className="mt-0.5 shrink-0"
        />
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex flex-wrap items-center gap-2">
            <span className="rounded bg-surface-container px-1.5 py-0.5 font-mono text-[10px] font-semibold text-on-surface-variant">
              {finding.category}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] text-on-surface-variant">
              {finding.source === "agentic" ? (
                <>
                  <AgenticChip className="size-3 text-tertiary" /> Agéntico
                </>
              ) : (
                <>
                  <ShieldWeb className="size-3 text-primary" /> Web
                </>
              )}
            </span>
          </div>
          <p className="text-sm font-medium leading-snug text-foreground">
            {finding.title}
          </p>
        </div>
        <ChevronDown
          className="mt-1 size-4 shrink-0 text-on-surface-variant transition-transform group-data-[panel-open]:rotate-180"
          aria-hidden
        />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="space-y-4 border-t border-outline-variant p-4">
          <Field label="Descripción">{finding.description}</Field>

          {redacted ? (
            <RedactedEvidence />
          ) : (
            <EvidenceBlock finding={finding} />
          )}

          <Field label="Impacto">{finding.impact}</Field>
          <Field label="Remediación">{finding.remediation}</Field>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-on-surface-variant">
            <span>
              Confianza:{" "}
              <span className="font-medium text-foreground">
                {finding.confidence}
              </span>
            </span>
            {typeof finding.cvss === "number" && (
              <span>
                CVSS:{" "}
                <span className="font-mono font-medium text-foreground">
                  {finding.cvss.toFixed(1)}
                </span>
              </span>
            )}
            {finding.affectedUrl && (
              <span className="truncate font-mono">{finding.affectedUrl}</span>
            )}
          </div>

          {finding.references.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {finding.references.map((ref) => (
                <span
                  key={ref}
                  className="rounded-full border border-outline-variant bg-surface-container px-2 py-0.5 font-mono text-[11px] text-on-surface-variant"
                >
                  {ref}
                </span>
              ))}
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export type FindingAccordionProps = {
  findings: AnyFinding[];
};

/** Renders the full technical layer: critical/high findings open by default. */
export function FindingAccordion({ findings }: FindingAccordionProps) {
  return (
    <div className="space-y-3">
      {findings.map((f) => (
        <FindingAccordionItem
          key={f.id}
          finding={f}
          defaultOpen={f.severity === "critical"}
        />
      ))}
    </div>
  );
}
