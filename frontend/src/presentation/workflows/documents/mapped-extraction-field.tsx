"use client";

import { Badge } from "@/src/presentation/components/ui/badge";
import { cn } from "@/src/application/lib/utils";
import {
  confidenceBand,
  formatConfidencePct,
  type ConfidenceBand,
} from "@/src/application/lib/format-confidence";

// Confidence signature: a value Doxiq is unsure about must look unsure.
// `-deep` tokens keep the percentage legible on the white surface; the dot
// carries the brighter band colour.
const BAND_STYLES: Record<ConfidenceBand, { dot: string; text: string }> = {
  high: { dot: "bg-success", text: "text-success-deep" },
  medium: { dot: "bg-warning", text: "text-warning-deep" },
  low: { dot: "bg-destructive", text: "text-destructive-deep" },
};

export interface MappedExtractionFieldValue {
  value: unknown;
  page_number: number | null;
  bbox?: Array<{ page_number: number; confidence?: number | null }>;
  ocr_confidence?: number | null;
  inferred: boolean;
}

export function renderExtractedValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(renderExtractedValue).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface MappedExtractionFieldProps {
  fieldKey: string;
  field: MappedExtractionFieldValue;
  isActive: boolean;
  onSelect?: (fieldKey: string) => void;
}

export function MappedExtractionField({
  fieldKey,
  field,
  isActive,
  onSelect,
}: MappedExtractionFieldProps) {
  const targetPage = field.bbox?.[0]?.page_number ?? field.page_number;
  const rawConfidence =
    field.ocr_confidence ?? field.bbox?.[0]?.confidence ?? null;
  const confidencePct =
    rawConfidence != null ? formatConfidencePct(rawConfidence) : null;
  const band = rawConfidence != null ? BAND_STYLES[confidenceBand(rawConfidence)] : null;

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect?.(fieldKey)}
        aria-pressed={isActive}
        className={cn(
          "w-full text-left rounded-lg border border-transparent",
          "px-3 py-2 transition-colors cursor-pointer",
          "hover:bg-muted/60 hover:border-border/60",
          isActive && "bg-primary/10 border-primary/40"
        )}
      >
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-xs font-mono text-muted-foreground">
            {fieldKey}
          </span>
          {targetPage ? (
            <span className="text-[10px] font-mono tracking-wider text-muted-foreground tabular-nums shrink-0">
              Pag.{targetPage}
            </span>
          ) : null}
        </div>
        <div className="mt-0.5 flex items-baseline justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2 text-sm font-medium break-all">
            {renderExtractedValue(field.value)}
            {field.inferred ? (
              <Badge
                variant="secondary"
                className="h-4 text-[9px] px-1.5 uppercase tracking-wider"
              >
                inferred
              </Badge>
            ) : null}
          </span>
          {confidencePct != null && band ? (
            <span className="flex shrink-0 items-center gap-1.5 text-[10px] font-mono tracking-wider tabular-nums">
              <span className="text-muted-foreground">Confianza:</span>
              <span
                aria-hidden
                className={cn("size-1.5 rounded-full", band.dot)}
              />
              <span className={cn("font-medium", band.text)}>
                {confidencePct}%
              </span>
            </span>
          ) : null}
        </div>
      </button>
    </li>
  );
}
