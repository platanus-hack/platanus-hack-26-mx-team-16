"use client";

import { ReactNode } from "react";
import { cn } from "@/src/application/lib/utils";
import type { DoctypeRef } from "@/src/presentation/components/prompt-editor";

const BRACE_TOKEN = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_.\-]*)\s*\}\}/g;
const DOCTYPE_TOKEN = /@([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)/g;

interface HighlightPromptProps {
  text: string;
  /** Paths valid inside `{{...}}` (field references). */
  paths?: string[];
  /** Doctypes valid as `@name[.path]` references. */
  doctypes?: DoctypeRef[];
  /** System variables valid inside `{{...}}` (takes precedence over `paths`). */
  systemVariables?: string[];
  className?: string;
}

export function HighlightPrompt({
  text,
  paths,
  doctypes,
  systemVariables,
  className,
}: HighlightPromptProps) {
  const bracePathSet = new Set(paths ?? []);
  const sysvarSet = new Set(systemVariables ?? []);
  const doctypeByName = new Map<string, DoctypeRef>();
  (doctypes ?? []).forEach((d) => doctypeByName.set(d.name, d));
  const systemVarsEnabled = (systemVariables?.length ?? 0) > 0;
  const doctypesEnabled = (doctypes?.length ?? 0) > 0;

  const isValidBrace = (inner: string) =>
    systemVarsEnabled ? sysvarSet.has(inner) : bracePathSet.has(inner);

  const isValidDoctype = (inner: string) => {
    const [name, ...rest] = inner.split(".");
    const dt = doctypeByName.get(name);
    if (!dt) return false;
    if (rest.length === 0) return true;
    return dt.paths.includes(rest.join("."));
  };

  type Match = {
    index: number;
    end: number;
    full: string;
    kind: "brace" | "doctype";
    inner: string;
  };
  const matches: Match[] = [];

  if (doctypesEnabled) {
    const re = new RegExp(DOCTYPE_TOKEN.source, "g");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      matches.push({
        index: m.index,
        end: m.index + m[0].length,
        full: m[0],
        inner: m[1],
        kind: "doctype",
      });
    }
  }
  {
    const re = new RegExp(BRACE_TOKEN.source, "g");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      matches.push({
        index: m.index,
        end: m.index + m[0].length,
        full: m[0],
        inner: m[1],
        kind: "brace",
      });
    }
  }
  matches.sort((a, b) => a.index - b.index);

  // Drop overlaps (first wins)
  const filtered: Match[] = [];
  let cursor = -1;
  for (const m of matches) {
    if (m.index >= cursor) {
      filtered.push(m);
      cursor = m.end;
    }
  }

  const nodes: ReactNode[] = [];
  let last = 0;
  for (const m of filtered) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const ok =
      m.kind === "brace" ? isValidBrace(m.inner) : isValidDoctype(m.inner);
    nodes.push(
      <span
        key={`${m.kind}-${m.index}`}
        className={cn(
          "rounded-sm font-medium",
          ok
            ? "bg-primary/15 text-primary ring-1 ring-primary/25"
            : "bg-destructive/10 text-destructive ring-1 ring-destructive/25"
        )}
      >
        {m.full}
      </span>
    );
    last = m.end;
  }
  if (last < text.length) nodes.push(text.slice(last));

  return <span className={className}>{nodes}</span>;
}
