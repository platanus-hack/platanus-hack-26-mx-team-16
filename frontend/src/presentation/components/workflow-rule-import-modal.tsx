"use client";

import { useState } from "react";
import type {
  ImportConflictStrategy,
  WorkflowRuleExportEnvelope,
  WorkflowRuleImportReport,
} from "@/src/domain/entities/workflow-rule-export";
import { isErrorFeedback, showErrorItems } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowRuleImportExportRepository } from "@/src/infrastructure/repositories/http-workflow-rule-import-export";
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

const repo = new HttpWorkflowRuleImportExportRepository(authHttp);

const STRATEGY_LABELS: Record<ImportConflictStrategy, string> = {
  SKIP: "Saltar conflictos",
  OVERWRITE: "Sobrescribir",
  RENAME: "Renombrar con sufijo",
  FAIL: "Abortar al primer conflicto",
};

interface WorkflowRuleImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
  onImported?: () => void;
}

export function WorkflowRuleImportModal({
  open,
  onOpenChange,
  workflowId,
  onImported,
}: WorkflowRuleImportModalProps) {
  const [envelope, setEnvelope] = useState<WorkflowRuleExportEnvelope | null>(null);
  const [report, setReport] = useState<WorkflowRuleImportReport | null>(null);
  const [strategy, setStrategy] = useState<ImportConflictStrategy>("SKIP");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setEnvelope(null);
    setReport(null);
    setError(null);
    setStrategy("SKIP");
  };

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as WorkflowRuleExportEnvelope;
      setEnvelope(parsed);
      setError(null);
      const preview = await repo.preview(workflowId, parsed);
      if (isErrorFeedback(preview)) {
        setError(showErrorItems(preview.errors));
        setReport(null);
      } else {
        setReport(preview);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
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
          <DialogTitle>Importar reglas</DialogTitle>
        </DialogHeader>

        <DialogBody className="-mx-6 px-6 gap-3">
          {!envelope ? (
            <div className="flex flex-col gap-1.5">
              <Label>Archivo de export (.json)</Label>
              <input
                type="file"
                accept="application/json"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-3 rounded border bg-muted/30 p-3 text-sm">
              <p>
                <strong>{envelope.rules.length}</strong> regla(s) detectadas (schema{" "}
                {envelope.schemaVersion}).
              </p>
              {report ? <ReportSummary report={report} /> : null}
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs">Estrategia ante conflictos</Label>
                <Select
                  value={strategy}
                  onValueChange={(next) => {
                    if (!next) return;
                    setStrategy(next as ImportConflictStrategy);
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
            Cerrar
          </Button>
          <Button disabled={!envelope || busy} onClick={handleConfirm}>
            {busy ? "Importando…" : "Confirmar import"}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function ReportSummary({ report }: { report: WorkflowRuleImportReport }) {
  return (
    <ul className="grid grid-cols-2 gap-1 text-xs">
      <li>Crear: {report.created}</li>
      <li>Sobrescribir: {report.overwritten}</li>
      <li>Saltar: {report.skipped}</li>
      <li>Renombrar: {report.renamed}</li>
      <li>Errores: {report.failed}</li>
      {report.unresolvedKbRefs.length > 0 ? (
        <li className="col-span-2">KB no resueltos: {report.unresolvedKbRefs.join(", ")}</li>
      ) : null}
      {report.unresolvedDocTypeSlugs.length > 0 ? (
        <li className="col-span-2">
          Slugs no resueltos: {report.unresolvedDocTypeSlugs.join(", ")}
        </li>
      ) : null}
    </ul>
  );
}
