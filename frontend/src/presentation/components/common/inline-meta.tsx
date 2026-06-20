"use client";

import type { ReactNode } from "react";

import { cn } from "src/application/lib/utils";

type InlineMetaVariant = "default" | "text" | "error";

const VARIANT_CLASSES: Record<InlineMetaVariant, string> = {
  /** Valores numéricos / identificadores (duraciones, contadores). */
  default: "shrink-0 font-mono tabular-nums text-foreground/70",
  /** Texto en prosa, no monoespaciado, con truncado. */
  text: "truncate text-foreground/70",
  /** Mensaje de error en prosa con tono rojo tenue. */
  error: "truncate text-red-500/80",
};

interface InlineMetaProps {
  /** Si es ``null``/``undefined``/``""`` no renderiza nada (ni el separador). */
  children: ReactNode;
  /** Selecciona la tipografía y tono. Por defecto ``"default"`` (mono). */
  variant?: InlineMetaVariant;
  /** Clases extra que se aplican al span del valor. */
  className?: string;
}

/**
 * Item dentro de una línea de metadatos: separador "·" tenue + valor.
 *
 * Diseñado para componer secuencias del estilo
 * ``Hace 5 min · 1m 23s · No se pudo iniciar`` sin repetir el separador
 * en cada caller. Las variantes mapean a tipografías predefinidas para
 * que el caller exprese intent (``"error"`` vs ``"default"``) en lugar
 * de pasar Tailwind classes a mano.
 */
export function InlineMeta({
  children,
  variant = "default",
  className,
}: InlineMetaProps) {
  if (children == null || children === "") return null;
  return (
    <>
      <span aria-hidden className="text-muted-foreground/40">
        ·
      </span>
      <span className={cn(VARIANT_CLASSES[variant], className)}>
        {children}
      </span>
    </>
  );
}
