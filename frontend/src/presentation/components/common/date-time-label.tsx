"use client";

import { formatDateTime } from "src/application/lib/format-date-time";
import { cn } from "src/application/lib/utils";

interface DateTimeLabelProps {
  /** ISO date string. ``null``/``undefined``/inválido renderiza el ``fallback``. */
  value: string | null | undefined;
  /** Texto a mostrar cuando ``value`` no produce una fecha válida. */
  fallback?: string;
  className?: string;
}

/**
 * Muestra una fecha+hora en formato "dd/Mes/yyyy HH:mm" (español).
 * El ISO crudo queda accesible en hover vía ``title``.
 */
export function DateTimeLabel({
  value,
  fallback = "—",
  className,
}: DateTimeLabelProps) {
  const formatted = formatDateTime(value);
  return (
    <span
      title={value ?? undefined}
      className={cn("truncate tabular-nums", className)}
    >
      {formatted ?? fallback}
    </span>
  );
}
