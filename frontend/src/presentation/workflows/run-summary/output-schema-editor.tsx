"use client";

import { Settings2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useMemo } from "react";

import { cn } from "@/src/application/lib/utils";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { SchemaPreview } from "@/src/presentation/components/json-schema-builder/schema-preview/schema-preview";
import { Label } from "@/src/presentation/components/ui/label";
import { Switch } from "@/src/presentation/components/ui/switch";
import { OutputSchemaListDetail } from "./output-schema-list-detail";

export const DEFAULT_OUTPUT_SCHEMA: JSONSchemaObject = {
  type: "object",
  required: ["verdict", "summary_text"],
  properties: {
    verdict: { enum: ["PASS", "FAIL", "REVIEW"] },
    summary_text: { type: "string" },
    key_findings: { type: "array", items: { type: "string" } },
    extracted_data: { type: "object" },
    citations: { type: "array" },
  },
};

interface OutputSchemaEditorProps {
  value: JSONSchemaObject | null;
  onChange: (schema: JSONSchemaObject | null) => void;
  errorMessage?: string | null;
  className?: string;
}

export function OutputSchemaEditor({
  value,
  onChange,
  errorMessage,
  className,
}: OutputSchemaEditorProps) {
  const t = useTranslations("OutputSchemaEditor");
  const usingDefault = value === null;
  const switchId = useId();
  const initialSchema = useMemo(
    () => value ?? DEFAULT_OUTPUT_SCHEMA,
    [value]
  );

  const handleToggle = (checked: boolean) => {
    if (checked) {
      onChange(null);
    } else {
      onChange(initialSchema);
    }
  };

  return (
    <section className={cn("space-y-4", className)}>
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
            {t("title")}
          </p>
          <p className="mt-1 text-sm text-muted-foreground/90">
            {t("description")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id={switchId}
            checked={usingDefault}
            onCheckedChange={handleToggle}
          />
          <Label htmlFor={switchId} className="text-xs">
            {t("useDefault")}
          </Label>
        </div>
      </header>

      {usingDefault ? (
        <div className="rounded-md border border-dashed bg-muted/30 px-4 py-3 text-sm text-muted-foreground/80">
          <Settings2 className="mr-2 inline size-3.5 -translate-y-0.5" />
          {t("defaultActive")}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 min-h-[420px]">
          <div className="rounded-md border border-border/50 bg-card flex flex-col overflow-hidden">
            <OutputSchemaListDetail
              value={initialSchema}
              onChange={(schema) => onChange(schema)}
            />
          </div>
          <div className="rounded-md border border-border/50 bg-card flex flex-col overflow-hidden">
            <SchemaPreview schema={initialSchema} />
          </div>
        </div>
      )}

      {errorMessage ? (
        <p className="text-xs text-destructive">{errorMessage}</p>
      ) : null}
    </section>
  );
}
