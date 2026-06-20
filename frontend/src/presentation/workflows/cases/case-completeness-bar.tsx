"use client";

import { Check, CircleDashed } from "lucide-react";

import type { CaseCompleteness } from "@/src/domain/entities/case";
import { Badge } from "@/src/presentation/components/ui/badge";

interface Props {
  completeness: CaseCompleteness;
  readyAt?: string | null;
  /** doc_type slug → nombre legible (de los documentGroups del caso). */
  docTypeNames?: Record<string, string>;
}

/**
 * E4 · Barra de completitud del expediente. Solo se renderiza cuando la
 * policy trae `required` no vacío: «2 de 3 documentos» + un chip por tipo
 * requerido (presente ✓ / faltante con contador). Near-flat: hairline ring
 * + whisper shadow, sin card anidada.
 */
export function CaseCompletenessBar({
  completeness,
  readyAt,
  docTypeNames = {},
}: Props) {
  const requiredEntries = Object.entries(completeness.required ?? {});
  if (requiredEntries.length === 0) return null;

  const totalRequired = requiredEntries.reduce((acc, [, n]) => acc + n, 0);
  const totalPresent = requiredEntries.reduce(
    (acc, [slug, n]) =>
      acc + Math.min(completeness.present?.[slug] ?? 0, n),
    0
  );
  const effectiveReadyAt = readyAt ?? completeness.readyAt;

  return (
    <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl bg-card px-4 py-2.5 shadow-xs ring-1 ring-foreground/10">
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          Completitud
        </span>
        <span className="text-sm font-medium">
          {totalPresent} de {totalRequired}{" "}
          {totalRequired === 1 ? "documento" : "documentos"}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {requiredEntries.map(([slug, requiredCount]) => {
          const presentCount = completeness.present?.[slug] ?? 0;
          const complete = presentCount >= requiredCount;
          const name = docTypeNames[slug] ?? slug;
          return (
            <Badge
              key={slug}
              variant={complete ? "success" : "warning"}
              title={
                complete
                  ? `${name}: completo`
                  : `${name}: faltan ${requiredCount - presentCount}`
              }
            >
              {complete ? <Check /> : <CircleDashed />}
              {name}
              <span className="font-mono">
                {Math.min(presentCount, requiredCount)}/{requiredCount}
              </span>
            </Badge>
          );
        })}
      </div>

      {effectiveReadyAt && (
        <span
          className="ml-auto font-mono text-xs text-muted-foreground"
          title="Momento en que el caso se marcó listo"
        >
          Listo:{" "}
          {new Date(effectiveReadyAt).toLocaleString("es", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </span>
      )}
    </div>
  );
}
