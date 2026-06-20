"use client";

import { Check, Copy, Download } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useDocumentTypeSchemaStore } from "src/application/stores/doctype-schema-store";
import type { DocumentType } from "src/domain/entities/doctype";
import { JsonViewer } from "src/presentation/components/json-viewer";
import { Button } from "src/presentation/components/ui/button";

interface SchemaTabProps {
  doctype: DocumentType;
}

export function DocumentTypeSchemaTab({ doctype }: SchemaTabProps) {
  const t = useTranslations("DoctypeSchemaTab");
  const schema = useDocumentTypeSchemaStore((s) => s.jsonSchema);
  const [copied, setCopied] = useState(false);
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const jsonString = useMemo(() => JSON.stringify(schema, null, 2), [schema]);

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    };
  }, []);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = jsonString;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    copiedTimerRef.current = setTimeout(() => setCopied(false), 2000);
  }, [jsonString]);

  const handleDownload = useCallback(() => {
    const slug =
      (doctype.name || "schema")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "") || "schema";
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [doctype.name, jsonString]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
        <span className="text-sm font-medium">{t("title")}</span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="xs"
            onClick={handleCopy}
            aria-label={t("copyAria")}
            aria-live="polite"
            className="gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-emerald-600 dark:text-emerald-400">
                  {t("copied")}
                </span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                {t("copy")}
              </>
            )}
          </Button>
          <Button
            variant="ghost"
            size="xs"
            onClick={handleDownload}
            aria-label={t("exportAria")}
            className="gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <Download className="h-3.5 w-3.5" />
            {t("export")}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <JsonViewer value={jsonString} />
      </div>
    </div>
  );
}
