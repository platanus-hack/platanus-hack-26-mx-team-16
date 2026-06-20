"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import { JsonViewer } from "@/src/presentation/components/json-viewer";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";

import { CitationChip, type CitationLike } from "./citation-chip";

interface NarrativeRendererProps {
  output: Record<string, unknown> | null;
  schema: Record<string, unknown> | null;
  onCitationNavigate?: (citation: CitationLike) => void;
  className?: string;
}

interface NodeContext {
  schema: Record<string, unknown> | null;
  /** When inside `properties.<name>`, surfaces the key for layout decisions. */
  fieldName: string | null;
  onCitationNavigate?: (citation: CitationLike) => void;
}

const VERDICT_KEYS = new Set(["verdict"]);
const CITATION_KEYS = new Set(["citations", "citation"]);
const KEY_FINDING_KEYS = new Set(["key_findings", "keyFindings", "findings"]);
const SUMMARY_TEXT_KEYS = new Set(["summary_text", "summaryText", "summary"]);

export function NarrativeRenderer({
  output,
  schema,
  onCitationNavigate,
  className,
}: NarrativeRendererProps) {
  const t = useTranslations("NarrativeRenderer");
  if (!output || typeof output !== "object") {
    return (
      <p className="text-sm text-muted-foreground/80">{t("noOutput")}</p>
    );
  }
  return (
    <div className={cn("space-y-6", className)}>
      <ObjectRenderer
        value={output}
        ctx={{ schema, fieldName: null, onCitationNavigate }}
        topLevel
      />
    </div>
  );
}

interface ObjectRendererProps {
  value: Record<string, unknown>;
  ctx: NodeContext;
  topLevel?: boolean;
}

function ObjectRenderer({ value, ctx, topLevel }: ObjectRendererProps) {
  const properties = readProperties(ctx.schema);
  const orderedKeys = orderedFieldNames(value, properties);

  if (orderedKeys.length === 0) {
    return <JsonViewer value={safeStringify(value)} />;
  }

  // For nested objects with simple key/value pairs, use the dl grid layout.
  const allScalar = orderedKeys.every((k) => isScalar(value[k]));
  if (allScalar && !topLevel) {
    return (
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
        {orderedKeys.map((key) => (
          <DlRow key={key} label={key} value={value[key]} />
        ))}
      </dl>
    );
  }

  return (
    <div className="space-y-6">
      {orderedKeys.map((key) => {
        if (VERDICT_KEYS.has(key)) return null; // already shown in hero
        const childSchema = properties?.[key] ?? null;
        return (
          <FieldBlock
            key={key}
            name={key}
            value={value[key]}
            schema={childSchema}
            onCitationNavigate={ctx.onCitationNavigate}
          />
        );
      })}
    </div>
  );
}

interface FieldBlockProps {
  name: string;
  value: unknown;
  schema: Record<string, unknown> | null;
  onCitationNavigate?: (c: CitationLike) => void;
}

function FieldBlock({ name, value, schema, onCitationNavigate }: FieldBlockProps) {
  const label = humanizeKey(name);

  if (CITATION_KEYS.has(name) && Array.isArray(value)) {
    return (
      <section className="space-y-2">
        <SectionLabel>{label}</SectionLabel>
        <ul className="flex flex-wrap gap-1.5">
          {value.map((c, idx) => (
            <li key={idx}>
              <CitationChip
                citation={c as CitationLike}
                onNavigate={onCitationNavigate}
              />
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (KEY_FINDING_KEYS.has(name) && Array.isArray(value)) {
    return (
      <section className="space-y-2">
        <SectionLabel>{label}</SectionLabel>
        <ul className="space-y-2 border-l-2 border-border pl-4">
          {value.map((item, idx) => (
            <li key={idx} className="text-sm leading-relaxed">
              {typeof item === "string" ? item : <JsonViewer value={safeStringify(item)} />}
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (SUMMARY_TEXT_KEYS.has(name) && typeof value === "string") {
    return (
      <section className="space-y-2">
        <SectionLabel>{label}</SectionLabel>
        <p className="font-serif text-base leading-relaxed text-foreground">
          {value}
        </p>
      </section>
    );
  }

  if (typeof value === "string") {
    return (
      <section className="space-y-1.5">
        <SectionLabel>{label}</SectionLabel>
        <p className="text-sm leading-relaxed text-foreground">{value}</p>
      </section>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <section className="space-y-1.5">
          <SectionLabel>{label}</SectionLabel>
          <p className="text-sm text-muted-foreground/70">— sin datos —</p>
        </section>
      );
    }
    if (value.every((v) => typeof v === "string")) {
      return (
        <section className="space-y-2">
          <SectionLabel>{label}</SectionLabel>
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {value.map((v, idx) => (
              <li key={idx}>{v as string}</li>
            ))}
          </ul>
        </section>
      );
    }
    if (value.every((v) => typeof v === "object" && v !== null && !Array.isArray(v))) {
      const rows = value as Array<Record<string, unknown>>;
      const columns = collectKeys(rows);
      return (
        <section className="space-y-2">
          <SectionLabel>{label}</SectionLabel>
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((col) => (
                  <TableHead key={col}>{humanizeKey(col)}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, idx) => (
                <TableRow key={idx}>
                  {columns.map((col) => (
                    <TableCell key={col}>{toCellText(row[col])}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </section>
      );
    }
    return (
      <section className="space-y-2">
        <SectionLabel>{label}</SectionLabel>
        <JsonViewer value={safeStringify(value)} />
      </section>
    );
  }

  if (value !== null && typeof value === "object") {
    return (
      <section className="space-y-2">
        <SectionLabel>{label}</SectionLabel>
        <ObjectRenderer
          value={value as Record<string, unknown>}
          ctx={{ schema, fieldName: name }}
        />
      </section>
    );
  }

  return (
    <section className="space-y-1.5">
      <SectionLabel>{label}</SectionLabel>
      <p className="font-mono text-sm tabular-nums">{toCellText(value)}</p>
    </section>
  );
}

function DlRow({ label, value }: { label: string; value: unknown }) {
  return (
    <>
      <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/70 self-center">
        {humanizeKey(label)}
      </dt>
      <dd className="font-medium text-foreground tabular-nums">
        {toCellText(value)}
      </dd>
    </>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
      {children}
    </h4>
  );
}

// ---------------- helpers ---------------- //

function readProperties(
  schema: Record<string, unknown> | null
): Record<string, Record<string, unknown>> | null {
  if (!schema) return null;
  const props = schema.properties;
  if (!props || typeof props !== "object") return null;
  return props as Record<string, Record<string, unknown>>;
}

function orderedFieldNames(
  value: Record<string, unknown>,
  schemaProperties: Record<string, unknown> | null
): string[] {
  const valueKeys = Object.keys(value);
  if (!schemaProperties) return valueKeys;
  const schemaKeys = Object.keys(schemaProperties);
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const k of schemaKeys) {
    if (k in value) {
      ordered.push(k);
      seen.add(k);
    }
  }
  for (const k of valueKeys) {
    if (!seen.has(k)) ordered.push(k);
  }
  return ordered;
}

function isScalar(v: unknown): boolean {
  return (
    v === null ||
    typeof v === "string" ||
    typeof v === "number" ||
    typeof v === "boolean"
  );
}

function collectKeys(rows: Array<Record<string, unknown>>): string[] {
  const keys: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (!seen.has(k)) {
        seen.add(k);
        keys.push(k);
      }
    }
  }
  return keys;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^\w/, (c) => c.toUpperCase());
}

function toCellText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return safeStringify(value);
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}
