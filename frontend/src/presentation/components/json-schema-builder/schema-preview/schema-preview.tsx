"use client";

import { useState } from "react";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Button } from "@/src/presentation/components/ui/button";
import { JsonViewer } from "@/src/presentation/components/json-viewer";
import { ScrollArea } from "@/src/presentation/components/ui/scroll-area";
import { Copy, Check, Download } from "lucide-react";
import {
  exportSchemaAsJSON,
  copySchemaToClipboard,
  exportSchemaAsFile,
} from "@/src/application/use-cases/json-schema/export-schema";

interface SchemaPreviewProps {
  schema: JSONSchemaObject;
}

export function SchemaPreview({ schema }: SchemaPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copySchemaToClipboard(schema);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    exportSchemaAsFile(schema, "schema.json");
  };

  const jsonString = exportSchemaAsJSON(schema, true);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          PREVIEW
        </h3>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={copied}
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy
              </>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4">
          <JsonViewer value={jsonString} />
        </div>
      </ScrollArea>
    </div>
  );
}
