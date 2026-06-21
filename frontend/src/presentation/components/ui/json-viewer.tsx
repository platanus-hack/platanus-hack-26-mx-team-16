"use client";

import type { CSSProperties } from "react";
import { useCallback, useMemo } from "react";
import { Download } from "lucide-react";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import oneDark from "react-syntax-highlighter/dist/esm/styles/prism/one-dark";
import oneLight from "react-syntax-highlighter/dist/esm/styles/prism/one-light";
import vscDarkPlus from "react-syntax-highlighter/dist/esm/styles/prism/vsc-dark-plus";

import { cn } from "@/src/application/lib/utils";

SyntaxHighlighter.registerLanguage("json", json);

/**
 * Theme registry. Adding a new theme = importing a style object from
 * `react-syntax-highlighter/dist/esm/styles/prism/*` and adding an entry
 * here. The map is the only place that knows about the available
 * themes, so the rest of the app can swap them via the `theme` prop.
 */
const THEME_MAP = {
  oneDark,
  oneLight,
  vscDarkPlus,
} satisfies Record<string, { [key: string]: CSSProperties }>;

export type JsonViewerTheme = keyof typeof THEME_MAP;

interface JsonViewerProps {
  /** Anything JSON-serialisable. Falls back to `String(value)` on cycles. */
  value: unknown;
  /** Defaults to `oneDark` (Linear/editor feel). */
  theme?: JsonViewerTheme;
  /** Show the left gutter with line numbers (default `true`). */
  showLineNumbers?: boolean;
  /**
   * Filename for the download action (including `.json` extension).
   * When omitted, the download button is hidden.
   */
  downloadFileName?: string;
  className?: string;
}

export function JsonViewer({
  value,
  theme = "oneDark",
  showLineNumbers = true,
  downloadFileName,
  className,
}: JsonViewerProps) {
  const code = useMemo(() => {
    try {
      return JSON.stringify(value, null, 2) ?? "null";
    } catch {
      return String(value);
    }
  }, [value]);

  const handleDownload = useCallback(() => {
    if (!downloadFileName) return;
    const blob = new Blob([code], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadFileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, [code, downloadFileName]);

  return (
    <div
      className={cn(
        "relative rounded-md border border-border/60 overflow-hidden",
        // Unified scrollbar with the rest of the app
        "[&_pre]:!m-0",
        "[&_pre]:![scrollbar-width:thin]",
        "[&_pre]:[scrollbar-color:transparent_transparent]",
        "hover:[&_pre]:[scrollbar-color:color-mix(in_oklab,var(--muted-foreground)_35%,transparent)_transparent]",
        "[&_pre::-webkit-scrollbar]:w-1.5 [&_pre::-webkit-scrollbar]:h-1.5",
        "[&_pre::-webkit-scrollbar-track]:bg-transparent",
        "[&_pre::-webkit-scrollbar-thumb]:rounded-full [&_pre::-webkit-scrollbar-thumb]:bg-transparent",
        "[&_pre::-webkit-scrollbar-thumb]:transition-colors [&_pre::-webkit-scrollbar-thumb]:duration-200",
        "hover:[&_pre::-webkit-scrollbar-thumb]:bg-muted-foreground/30",
        "[&_pre::-webkit-scrollbar-thumb:hover]:bg-muted-foreground/60",
        className,
      )}
    >
      {downloadFileName ? (
        <button
          type="button"
          onClick={handleDownload}
          title={`Descargar ${downloadFileName}`}
          aria-label={`Descargar ${downloadFileName}`}
          className={cn(
            "absolute top-2 right-2 z-10 inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-md",
            "border border-outline-variant/30 bg-surface-container-high/70 text-on-surface-variant backdrop-blur-sm",
            "transition-colors hover:bg-surface-container-highest hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
          )}
        >
          <Download className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : null}

      <SyntaxHighlighter
        language="json"
        style={THEME_MAP[theme]}
        showLineNumbers={showLineNumbers}
        wrapLongLines={false}
        lineNumberStyle={{
          minWidth: "2.5em",
          paddingRight: "1em",
          color: "color-mix(in oklab, var(--muted-foreground) 50%, transparent)",
          userSelect: "none",
          textAlign: "right",
        }}
        customStyle={{
          margin: 0,
          padding: "0.875rem 1rem",
          paddingRight: downloadFileName ? "3rem" : "1rem",
          fontSize: "12px",
          lineHeight: 1.55,
        }}
        codeTagProps={{
          style: {
            fontFamily:
              "var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, monospace",
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
