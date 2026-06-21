"use client";

import type { LucideIcon } from "lucide-react";

import { cn } from "src/application/lib/utils";

const RING_SIZE = 30; // diámetro en px
const RING_STROKE = 2;
const RING_RADIUS = (RING_SIZE - RING_STROKE) / 2;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

export interface StatusRingProps {
  /**
   * Tailwind color class aplicado al arco (modo live) y al icono central.
   * Ej: "text-violet-500".
   */
  tone: string;
  /** Cuando es true, el arco se rellena proporcionalmente a ``pct``. */
  isLive: boolean;
  /** Progreso 0-100 (solo aplica en modo live). */
  pct: number;
  /** Icono central. En modo live se reemplaza por el porcentaje. */
  icon: LucideIcon;
  /**
   * Cuando ``isLive`` es false y se proporciona ``bg``, el círculo se
   * rellena por completo con esa clase (típicamente algo como
   * "bg-success/15"). Si se omite, en modo terminal se dibuja el
   * arco completo como anillo decorativo.
   */
  bg?: string;
  /** Anima el icono central con spin (útil para estados transitorios). */
  spinIcon?: boolean;
}

/**
 * Indicador de estado tipo App Store con dos modos:
 * - **Live**: anillo abierto con arco proporcional + ``%`` al centro.
 * - **Terminal**: círculo lleno (si se pasa ``bg``) con icono central.
 *
 * El icono debería ser una glifo "limpia" (Check, X, Minus) cuando se usa
 * con fondo lleno; íconos que ya incluyen un círculo (CheckCircle2) crean
 * un doble-círculo visual.
 */
export function StatusRing({
  tone,
  bg,
  isLive,
  pct,
  icon: Icon,
  spinIcon = false,
}: StatusRingProps) {
  return (
    <div
      style={{ width: RING_SIZE, height: RING_SIZE }}
      className={cn(
        "relative flex shrink-0 items-center justify-center rounded-full",
        !isLive && bg
      )}
    >
      {isLive || !bg ? (
        <ProgressArc tone={tone} isLive={isLive} pct={pct} />
      ) : null}
      <span className="absolute inset-0 flex items-center justify-center">
        {isLive ? (
          <span
            className={cn(
              "font-mono text-[9px] font-semibold tabular-nums",
              tone
            )}
          >
            {pct}
          </span>
        ) : (
          <Icon className={cn("size-4", tone, spinIcon && "animate-spin")} />
        )}
      </span>
    </div>
  );
}

function ProgressArc({
  tone,
  isLive,
  pct,
}: {
  tone: string;
  isLive: boolean;
  pct: number;
}) {
  const visiblePct = isLive ? Math.max(3, pct) : 100;
  const offset = RING_CIRCUMFERENCE - (visiblePct / 100) * RING_CIRCUMFERENCE;
  return (
    <svg
      width={RING_SIZE}
      height={RING_SIZE}
      aria-hidden
      className="-rotate-90"
    >
      <circle
        cx={RING_SIZE / 2}
        cy={RING_SIZE / 2}
        r={RING_RADIUS}
        fill="none"
        strokeWidth={RING_STROKE}
        className="stroke-muted-foreground/15"
      />
      <circle
        cx={RING_SIZE / 2}
        cy={RING_SIZE / 2}
        r={RING_RADIUS}
        fill="none"
        strokeWidth={RING_STROKE}
        strokeLinecap="round"
        strokeDasharray={RING_CIRCUMFERENCE}
        strokeDashoffset={offset}
        style={{ stroke: "currentColor" }}
        className={cn(
          tone,
          "transition-[stroke-dashoffset] duration-500 ease-out"
        )}
      />
    </svg>
  );
}
