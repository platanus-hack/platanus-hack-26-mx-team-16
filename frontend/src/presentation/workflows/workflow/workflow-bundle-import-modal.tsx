"use client";

import { useState } from "react";

import type {
  BundleImportStrategy,
  WorkflowBundleEnvelope,
  WorkflowBundleImportReport,
} from "@/src/domain/entities/workflow-bundle-export";
import {
  isErrorFeedback,
  showErrorItems,
} from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowBundleImportExportRepository } from "@/src/infrastructure/repositories/http-workflow-bundle-import-export";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";

const repo = new HttpWorkflowBundleImportExportRepository(authHttp);

const STRATEGY_LABELS: Record<BundleImportStrategy, string> = {
  skip: "Saltar conflictos",
  overwrite: "Sobrescribir",
  rename: "Renombrar con sufijo",
  fail: "Abortar al primer conflicto",
};

interface WorkflowBundleImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
  onImported?: () => void;
}

export function WorkflowBundleImportModal({
  open,
  onOpenChange,
  workflowId,
  onImported,
}: WorkflowBundleImportModalProps) {
  const [envelope, setEnvelope] = useState<WorkflowBundleEnvelope | null>(null);
  const [report, setReport] = useState<WorkflowBundleImportReport | null>(null);
  const [applied, setApplied] = useState(false);
  const [strategy, setStrategy] = useState<BundleImportStrategy>("skip");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setEnvelope(null);
    setReport(null);
    setApplied(false);
    setError(null);
    setStrategy("skip");
  };

  const runPreview = async (
    payload: WorkflowBundleEnvelope,
    next: BundleImportStrategy,
  ) => {
    setBusy(true);
    setError(null);
    const preview = await repo.preview(workflowId, payload, next);
    setBusy(false);
    if (isErrorFeedback(preview)) {
      setError(showErrorItems(preview.errors));
      setReport(null);
    } else {
      setReport(preview);
    }
  };

  const handleFile = async (file: File) => {
    setBusy(true);
    setApplied(false);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as WorkflowBundleEnvelope;
      setEnvelope(parsed);
      setError(null);
      setBusy(false);
      await runPreview(parsed, strategy);
    } catch (err) {
      setBusy(false);
      setError((err as Error).message);
    }
  };

  const handleStrategyChange = (next: BundleImportStrategy) => {
    setStrategy(next);
    setApplied(false);
    if (envelope) void runPreview(envelope, next);
  };

  const handleConfirm = async () => {
    if (!envelope) return;
    setBusy(true);
    const result = await repo.run(workflowId, envelope, strategy);
    setBusy(false);
    if (isErrorFeedback(result)) {
      setError(showErrorItems(result.errors));
      return;
    }
    setReport(result);
    setApplied(true);
    onImported?.();
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogBackdrop />
      <DialogPopup className="max-w-xl p-6">
        <DialogHeader>
          <DialogTitle>Importar configuración del workflow</DialogTitle>
        </DialogHeader>

        <DialogBody className="-mx-6 gap-3 px-6">
          {!envelope ? (
            <div className="flex flex-col gap-1.5">
              <Label>Archivo de export del workflow (.json)</Label>
              <input
                type="file"
                accept="application/json"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
              <p className="text-xs text-muted-foreground">
                Incluye tipos de documento, pipeline (receta + políticas) y
                reglas. No incluye orígenes, destinos ni secretos.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3 rounded border bg-muted/30 p-3 text-sm">
              {applied ? (
                <p className="font-medium text-success-deep">
                  Importación aplicada.
                </p>
              ) : (
                <p className="text-muted-foreground">
                  Vista previa (no se ha escrito nada todavía).
                </p>
              )}
              {report ? <ReportSummary report={report} /> : null}
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs">Estrategia ante conflictos</Label>
                <Select
                  value={strategy}
                  onValueChange={(next) => {
                    if (!next) return;
                    handleStrategyChange(next as BundleImportStrategy);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(STRATEGY_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {error ? <p className="text-xs text-red-700">{error}</p> : null}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {applied ? "Cerrar" : "Cancelar"}
          </Button>
          {!applied && (
            <Button disabled={!envelope || busy} onClick={handleConfirm}>
              {busy ? "Importando…" : "Confirmar import"}
            </Button>
          )}
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function ReportSummary({ report }: { report: WorkflowBundleImportReport }) {
  return (
    <div className="flex flex-col gap-2 text-xs">
      <Section
        title="Tipos de documento"
        items={[
          ["Crear", report.documentTypes.created],
          ["Sobrescribir", report.documentTypes.overwritten],
          ["Saltar", report.documentTypes.skipped],
          ["Errores", report.documentTypes.failed],
        ]}
      />
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span className="font-medium text-muted-foreground">Pipeline:</span>
        <span>
          {report.pipeline.slug ?? "—"}
          {report.pipeline.version != null
            ? ` · v${report.pipeline.version}`
            : ""}
          {report.pipeline.created ? " (nueva versión)" : ""}
          {report.pipeline.bound ? " · vinculado" : ""}
        </span>
      </div>
      <Section
        title="Reglas"
        items={[
          ["Crear", report.rules.created],
          ["Sobrescribir", report.rules.overwritten],
          ["Saltar", report.rules.skipped],
          ["Renombrar", report.rules.renamed],
          ["Errores", report.rules.failed],
        ]}
      />
      {report.recompilationScheduled > 0 ? (
        <p className="text-muted-foreground">
          Recompilación programada: {report.recompilationScheduled} regla(s).
        </p>
      ) : null}
      {report.unresolvedKbRefs.length > 0 ? (
        <p>KB no resueltos: {report.unresolvedKbRefs.join(", ")}</p>
      ) : null}
      {report.unresolvedDocTypeSlugs.length > 0 ? (
        <p>Slugs no resueltos: {report.unresolvedDocTypeSlugs.join(", ")}</p>
      ) : null}
      {report.errors.length > 0 ? (
        <p className="text-red-700">{report.errors.join(" · ")}</p>
      ) : null}
    </div>
  );
}

function Section({
  title,
  items,
}: {
  title: string;
  items: Array<[string, number]>;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <span className="font-medium text-muted-foreground">{title}:</span>
      {items.map(([label, value]) => (
        <span key={label}>
          {label} {value}
        </span>
      ))}
    </div>
  );
}
