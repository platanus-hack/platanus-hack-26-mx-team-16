"use client";

import { cn } from "src/application/lib/utils";

interface ShortIdProps {
  /** Identificador completo (uuid u otro string largo) del que se renderiza un prefijo. */
  value: string | null | undefined;
  /** Cantidad de caracteres a mostrar. */
  length?: number;
  /** Prefijo visual antes del id corto. */
  prefix?: string;
  className?: string;
}

/**
 * Átomo visual para identificadores compactos y escaneables: mono uppercase
 * con tracking ancho para leerse como un serial / hash. El valor completo
 * queda accesible vía ``title`` en hover.
 */
export function ShortId({
  value,
  length = 8,
  prefix = "#",
  className,
}: ShortIdProps) {
  if (!value) return null;
  return (
    <span
      title={value}
      className={cn(
        "shrink-0 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/50",
        className
      )}
    >
      {prefix}
      {value.slice(0, length)}
    </span>
  );
}
