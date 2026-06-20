"use client";

import { Download, Upload } from "lucide-react";
import { useCallback, useState } from "react";

import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowBundleImportExportRepository } from "@/src/infrastructure/repositories/http-workflow-bundle-import-export";
import { Button } from "@/src/presentation/components/ui/button";
import { WorkflowBundleImportModal } from "./workflow-bundle-import-modal";

const repo = new HttpWorkflowBundleImportExportRepository(authHttp);

/**
 * E6 · W8 — Export/Import del bundle completo del workflow (doctypes +
 * pipeline + reglas). Header de los settings del workflow. Export descarga el
 * envelope como blob (patrón del export de reglas); Import abre el modal con
 * preview dry-run + selector de estrategia.
 */
export function WorkflowBundleActions({ workflowId }: { workflowId: string }) {
  const [importOpen, setImportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const envelope = await repo.export(workflowId);
      if (isErrorFeedback(envelope)) return;
      const blob = new Blob([JSON.stringify(envelope, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `workflow-${workflowId}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }, [workflowId]);

  return (
    <>
      <Button
        variant="outline"
        className="gap-2"
        onClick={() => setImportOpen(true)}
      >
        <Upload className="h-4 w-4" />
        Importar workflow
      </Button>
      <Button
        variant="outline"
        className="gap-2"
        onClick={handleExport}
        disabled={exporting}
      >
        <Download className="h-4 w-4" />
        Exportar workflow
      </Button>
      <WorkflowBundleImportModal
        open={importOpen}
        onOpenChange={setImportOpen}
        workflowId={workflowId}
      />
    </>
  );
}
