"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";

export interface TokenSpec {
  name: string;
  scope: "runtime" | "case" | "tenant" | "rule" | "run" | "workflow";
  description: string;
}

interface TokenChipPaletteProps {
  tokens: TokenSpec[];
  onInsert: (token: string) => void;
  className?: string;
}

const SCOPE_ORDER: TokenSpec["scope"][] = [
  "runtime",
  "case",
  "tenant",
  "rule",
  "run",
  "workflow",
];

const SCOPE_LABEL: Record<TokenSpec["scope"], string> = {
  runtime: "Runtime",
  case: "Case",
  tenant: "Tenant",
  rule: "Rule",
  run: "Run",
  workflow: "Workflow",
};

export function TokenChipPalette({
  tokens,
  onInsert,
  className,
}: TokenChipPaletteProps) {
  const t = useTranslations("TokenChipPalette");
  const grouped = SCOPE_ORDER.map((scope) => ({
    scope,
    items: tokens.filter((t) => t.scope === scope),
  })).filter((g) => g.items.length > 0);

  return (
    <div className={cn("space-y-3", className)}>
      <header className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground/70">
        {t("title")}
      </header>
      <ul className="space-y-3">
        {grouped.map(({ scope, items }) => (
          <li key={scope} className="space-y-1.5">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/60">
              {SCOPE_LABEL[scope]}
            </p>
            <ul className="flex flex-wrap gap-1.5">
              {items.map((t) => (
                <li key={t.name}>
                  <button
                    type="button"
                    onClick={() => onInsert(`{{${t.name}}}`)}
                    title={t.description}
                    className="inline-flex h-6 items-center rounded border border-border/70 px-2 font-mono text-[11px] text-muted-foreground/90 transition-colors hover:border-foreground/40 hover:text-foreground"
                  >
                    {`{{${t.name}}}`}
                  </button>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Mirror of the backend `token_registry.REGISTRY` (kept in sync manually). */
export const DEFAULT_TOKEN_REGISTRY: TokenSpec[] = [
  { name: "now", scope: "runtime", description: "Current ISO-8601 timestamp." },
  { name: "today", scope: "runtime", description: "Current date (YYYY-MM-DD)." },
  {
    name: "today.year",
    scope: "runtime",
    description: "Current year as integer.",
  },
  {
    name: "case.name",
    scope: "case",
    description: "Display name of the analysis case.",
  },
  {
    name: "tenant.name",
    scope: "tenant",
    description: "Display name of the tenant.",
  },
  {
    name: "rule.severity",
    scope: "rule",
    description: "Configured severity of the running rule.",
  },
  {
    name: "run.id",
    scope: "run",
    description: "UUID of the workflow analysis run.",
  },
  {
    name: "run.completed_at",
    scope: "run",
    description: "ISO-8601 timestamp of run completion.",
  },
];
