/**
 * ReportActions — Share + PDF actions for the full report (§F7). Client island.
 * Share → POST /api/owliver/scans/{id}/share → `{token}` → copies the absolute
 * `/r/{token}` link (TTL 7 días) and surfaces it inline (sonner not installed —
 * no new dep). PDF → GET /api/.../report.pdf via the backend (link, new tab).
 */
"use client";

import { Check, Link2, Loader2, FileDown } from "lucide-react";

import { useShareReport } from "@/src/application/owliver/hooks/use-share-report";
import { Button } from "@/src/presentation/components/ui/button";

export type ReportActionsProps = {
  scanId: string;
};

export function ReportActions({ scanId }: ReportActionsProps) {
  const { state, share } = useShareReport(scanId);
  const loading = state.status === "loading";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={share}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="animate-spin" aria-hidden />
          ) : state.status === "done" ? (
            <Check aria-hidden />
          ) : (
            <Link2 aria-hidden />
          )}
          {state.status === "done" ? "Enlace copiado" : "Compartir"}
        </Button>

        <a
          href={`/api/v1/scans/${scanId}/report.pdf`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-9 items-center gap-1.5 rounded-full border border-outline bg-transparent px-4 text-sm font-medium text-primary transition-colors hover:bg-accent"
        >
          <FileDown className="size-4" aria-hidden />
          Exportar PDF
        </a>
      </div>

      {state.status === "done" && (
        <p
          className="truncate font-mono text-xs text-on-surface-variant"
          aria-live="polite"
        >
          {state.url} · válido 7 días
        </p>
      )}
      {state.status === "error" && (
        <p className="text-xs text-destructive" aria-live="polite">
          {state.message}
        </p>
      )}
    </div>
  );
}
