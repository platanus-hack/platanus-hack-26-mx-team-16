"use client";

import { ExternalLink, FileWarning, X } from "lucide-react";
import type * as React from "react";

import { cn } from "@/src/application/lib/utils";
import type {
  Finding,
  FindingEvidence,
  Severity,
} from "@/src/application/owliver/schemas/api";
import type { LiveFinding } from "@/src/application/owliver/stores/theater-store";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogClose,
  DialogDescription,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { SeverityChip } from "@/src/presentation/owliver/components/severity-chip";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

type FindingDetail = Finding | LiveFinding;

export type FindingDetailDialogProps = {
  finding: FindingDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function isFullFinding(finding: FindingDetail): finding is Finding {
  return "id" in finding && typeof finding.description === "string";
}

function metaValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "Pendiente";
  return value;
}

function DetailField({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-1.5", className)}>
      <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant">
        {label}
      </h3>
      <div className="text-sm leading-relaxed text-foreground">{children}</div>
    </section>
  );
}

function MonoBlock({ label, children }: { label: string; children: string }) {
  return (
    <DetailField label={label}>
      <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-surface-container-lowest p-3 font-mono text-xs leading-relaxed text-on-surface-variant ring-1 ring-outline-variant">
        {children}
      </pre>
    </DetailField>
  );
}

function Evidence({ evidence }: { evidence?: FindingEvidence }) {
  if (!evidence || Object.keys(evidence).length === 0) {
    return (
      <div className="flex items-start gap-3 rounded-xl bg-surface-container p-3 text-sm text-on-surface-variant ring-1 ring-outline-variant">
        <FileWarning className="mt-0.5 size-4 shrink-0" aria-hidden />
        La evidencia completa todavía no está sincronizada con este stream.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {evidence.canary && (
        <div className="rounded-xl bg-destructive/10 p-3 ring-1 ring-destructive/40">
          <p className="mb-1 text-sm font-semibold text-destructive">
            Token canario filtrado
          </p>
          <p className="break-words font-mono text-sm font-semibold text-destructive">
            {evidence.canary}
          </p>
          {evidence.reason && (
            <p className="mt-1 text-xs text-on-surface-variant">
              {evidence.reason}
            </p>
          )}
        </div>
      )}
      {evidence.payload && (
        <MonoBlock label="Payload">{evidence.payload}</MonoBlock>
      )}
      {evidence.request && (
        <MonoBlock label="Solicitud">{evidence.request}</MonoBlock>
      )}
      {evidence.response && (
        <MonoBlock label="Respuesta">{evidence.response}</MonoBlock>
      )}
      {evidence.screenshot && (
        // biome-ignore lint/performance/noImgElement: FastAPI static evidence is not a Next image asset.
        <img
          src={evidence.screenshot}
          alt="Captura de evidencia del hallazgo"
          className="max-h-72 rounded-xl bg-surface-container object-contain ring-1 ring-outline-variant"
        />
      )}
    </div>
  );
}

function SourceTag({ source }: { source?: "owasp" | "agentic" }) {
  if (!source) return null;
  const Icon = source === "agentic" ? AgenticChip : ShieldWeb;
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-full bg-surface-container px-2.5 text-xs text-on-surface-variant">
      <Icon
        className={cn(
          "size-3.5",
          source === "agentic" ? "text-tertiary" : "text-primary"
        )}
        aria-hidden
      />
      {source === "agentic" ? "Agéntico" : "Web"}
    </span>
  );
}

export function FindingDetailDialog({
  finding,
  open,
  onOpenChange,
}: FindingDetailDialogProps) {
  const title = finding?.title ?? "Detalle del hallazgo";
  const severity = finding?.severity as Severity | undefined;
  const description = finding?.description;
  const affectedUrl = finding?.affectedUrl;
  const references = finding?.references ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop className="bg-black/60" />
      <DialogPopup className="soc max-w-3xl rounded-2xl bg-card p-0 text-foreground ring-1 ring-outline-variant">
        {finding && (
          <>
            <DialogHeader className="border-b border-outline-variant p-5 pr-14">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                {severity && <SeverityChip severity={severity} size="sm" />}
                {finding.category && (
                  <span className="inline-flex h-7 items-center rounded-full bg-surface-container px-2.5 font-mono text-[11px] font-semibold text-on-surface-variant">
                    {finding.category}
                  </span>
                )}
                <SourceTag source={finding.source} />
              </div>
              <DialogTitle className="text-balance text-xl leading-tight">
                {title}
              </DialogTitle>
              <DialogDescription className="text-on-surface-variant">
                {isFullFinding(finding)
                  ? "Evidencia y remediación del hallazgo autenticado."
                  : "Hallazgo recibido en vivo; se mostrará más detalle cuando el backend termine de persistir la evidencia."}
              </DialogDescription>
            </DialogHeader>

            <DialogClose
              render={
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Cerrar detalle del hallazgo"
                  className="absolute right-3 top-3 text-on-surface-variant hover:text-foreground"
                >
                  <X className="size-4" aria-hidden />
                </Button>
              }
            />

            <DialogBody className="gap-5 p-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-surface-container p-3 ring-1 ring-outline-variant">
                  <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-on-surface-variant">
                    Confianza
                  </p>
                  <p className="mt-1 text-sm font-semibold text-foreground">
                    {metaValue(finding.confidence)}
                  </p>
                </div>
                <div className="rounded-xl bg-surface-container p-3 ring-1 ring-outline-variant">
                  <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-on-surface-variant">
                    CVSS
                  </p>
                  <p className="mt-1 font-mono text-sm font-semibold text-foreground">
                    {typeof finding.cvss === "number"
                      ? finding.cvss.toFixed(1)
                      : "Pendiente"}
                  </p>
                </div>
                <div className="rounded-xl bg-surface-container p-3 ring-1 ring-outline-variant">
                  <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-on-surface-variant">
                    Herramienta
                  </p>
                  <p className="mt-1 truncate font-mono text-sm font-semibold text-foreground">
                    {metaValue(finding.tool)}
                  </p>
                </div>
              </div>

              {description && (
                <DetailField label="Descripción">{description}</DetailField>
              )}

              <DetailField label="Evidencia">
                <Evidence evidence={finding.evidence} />
              </DetailField>

              {finding.impact && (
                <DetailField label="Impacto">{finding.impact}</DetailField>
              )}

              {finding.remediation && (
                <DetailField label="Remediación">
                  {finding.remediation}
                </DetailField>
              )}

              {(affectedUrl || finding.endpoint || finding.param) && (
                <div className="grid gap-3 rounded-xl bg-surface-container p-3 ring-1 ring-outline-variant sm:grid-cols-3">
                  {affectedUrl && (
                    <DetailField label="URL afectada" className="sm:col-span-3">
                      <a
                        href={affectedUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex max-w-full items-center gap-1 break-all font-mono text-xs text-primary underline-offset-4 hover:underline"
                      >
                        {affectedUrl}
                        <ExternalLink className="size-3 shrink-0" aria-hidden />
                      </a>
                    </DetailField>
                  )}
                  {finding.endpoint && (
                    <DetailField label="Endpoint">
                      <span className="font-mono text-xs">
                        {finding.endpoint}
                      </span>
                    </DetailField>
                  )}
                  {finding.param && (
                    <DetailField label="Parámetro">
                      <span className="font-mono text-xs">{finding.param}</span>
                    </DetailField>
                  )}
                </div>
              )}

              {references.length > 0 && (
                <DetailField label="Referencias">
                  <div className="flex flex-wrap gap-2">
                    {references.map((reference) => (
                      <span
                        key={reference}
                        className="rounded-full bg-surface-container px-2.5 py-1 font-mono text-[11px] text-on-surface-variant ring-1 ring-outline-variant"
                      >
                        {reference}
                      </span>
                    ))}
                  </div>
                </DetailField>
              )}
            </DialogBody>
          </>
        )}
      </DialogPopup>
    </Dialog>
  );
}
