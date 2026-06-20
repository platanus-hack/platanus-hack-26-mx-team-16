"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/src/application/lib/utils";

interface PdfViewerLoadingProps {
  /** Primary copy; falls back to the localized "Cargando documento…". */
  label?: string;
  /** Adds a translucent backdrop when overlaying the viewer surface. */
  variant?: "surface" | "overlay";
  className?: string;
}

/**
 * Centered, animated placeholder shown while the PDF viewer (or its
 * underlying file) is loading. Designed to fill its parent container so
 * it always sits in the middle regardless of where the viewer is
 * mounted.
 */
export function PdfViewerLoading({
  label,
  variant = "surface",
  className,
}: PdfViewerLoadingProps) {
  const t = useTranslations("PdfViewer");
  const resolvedLabel = label ?? t("loading");
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={resolvedLabel}
      className={cn(
        "absolute inset-0 flex h-full w-full items-center justify-center",
        variant === "overlay"
          ? "bg-background/70 backdrop-blur-sm"
          : "bg-muted/30",
        className
      )}
    >
      <div className="flex flex-col items-center gap-4 px-6 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-foreground/80">
          {resolvedLabel}
        </p>

        {/* Animated triple-dot to underline the "in flight" feel */}
        <div className="flex items-center gap-1.5" aria-hidden>
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary/70"
            style={{ animation: "pdfviewer-dot 1.2s ease-in-out infinite" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary/70"
            style={{
              animation: "pdfviewer-dot 1.2s ease-in-out infinite",
              animationDelay: "0.15s",
            }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary/70"
            style={{
              animation: "pdfviewer-dot 1.2s ease-in-out infinite",
              animationDelay: "0.3s",
            }}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes pdfviewer-dot {
          0%,
          80%,
          100% {
            transform: scale(0.6);
            opacity: 0.35;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
