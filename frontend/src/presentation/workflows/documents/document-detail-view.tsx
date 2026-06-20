"use client";

import { ArrowLeft, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
// E5 · la carga vive en TanStack Query (`workflow-documents.ts`): la mutación
// de campos del bench actualiza la caché y esta vista se refresca sola.
import { useWorkflowDocumentQuery } from "@/src/application/hooks/queries/workflow-documents";
import { Button } from "@/src/presentation/components/ui/button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { DocumentViewerPane } from "@/src/presentation/workflows/documents/document-viewer-pane";
import { DocumentDataPane } from "@/src/presentation/workflows/documents/document-data-pane";

interface DocumentDetailViewProps {
  documentId: string;
}

export function DocumentDetailView({ documentId }: DocumentDetailViewProps) {
  const t = useTranslations("DocumentDetail");
  const router = useRouter();
  const { data: document, isLoading } = useWorkflowDocumentQuery(documentId);
  const [activeFieldKey, setActiveFieldKey] = useState<string | null>(null);

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!document) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        {t("notFound")}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </Button>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-mono">
                {document.fileName || t("fallbackName")}
              </h1>
              <Badge variant="outline">{document.status}</Badge>
            </div>
            <span className="text-xs text-muted-foreground">
              ID: {document.uuid}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("closeAria")}
          title={t("closeAria")}
          onClick={() => router.back()}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 flex-1 min-h-0">
        <div className="lg:col-span-2 min-h-0">
          <DocumentViewerPane
            document={document}
            activeFieldKey={activeFieldKey}
            onFieldSelect={(key) =>
              setActiveFieldKey((prev) => (prev === key ? null : key))
            }
          />
        </div>
        <div className="lg:col-span-1 min-h-0">
          <DocumentDataPane
            document={document}
            activeFieldKey={activeFieldKey}
            onFieldSelect={(key) =>
              setActiveFieldKey((prev) => (prev === key ? null : key))
            }
          />
        </div>
      </div>
    </div>
  );
}
