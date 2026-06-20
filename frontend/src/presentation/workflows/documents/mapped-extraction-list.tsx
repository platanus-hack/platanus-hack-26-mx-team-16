"use client";

import type { FieldVerificationMap } from "@/src/infrastructure/repositories/http-workflow-document";
import {
  MappedExtractionField,
  type MappedExtractionFieldValue,
} from "./mapped-extraction-field";

interface MappedExtractionListProps {
  entries: Array<[string, unknown]>;
  activeFieldKey?: string | null;
  onFieldSelect?: (fieldKey: string) => void;
  // E5 · bench editable: confianza, verificación y flags por campo.
  fieldConfidence?: Record<string, number | null>;
  verification?: FieldVerificationMap | null;
  flaggedFields?: ReadonlySet<string>;
  editable?: boolean;
  busyFieldKey?: string | null;
  onAccept?: (fieldKey: string) => void;
  onCorrect?: (fieldKey: string, value: unknown) => void;
}

export function MappedExtractionList({
  entries,
  activeFieldKey,
  onFieldSelect,
  fieldConfidence,
  verification,
  flaggedFields,
  editable = false,
  busyFieldKey,
  onAccept,
  onCorrect,
}: MappedExtractionListProps) {
  return (
    <ul className="space-y-1">
      {entries.map(([key, field]) => (
        <MappedExtractionField
          key={key}
          fieldKey={key}
          field={field as MappedExtractionFieldValue}
          isActive={activeFieldKey === key}
          onSelect={onFieldSelect}
          confidence={fieldConfidence?.[key] ?? null}
          verification={verification?.[key] ?? null}
          flagged={flaggedFields?.has(key) ?? false}
          editable={editable}
          busy={busyFieldKey === key}
          onAccept={onAccept}
          onCorrect={onCorrect}
        />
      ))}
    </ul>
  );
}
