"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useSessionStore } from "@/src/application/contexts/session-store";
import {
  fieldKeyToBoxId,
  mappedExtractionToBoxes,
} from "@/src/application/lib/mapped-extraction";
import type { WorkflowDocumentDetail } from "@/src/infrastructure/repositories/http-workflow-document";
import { PdfViewerLoading } from "@/src/presentation/components/ui/pdf-viewer-loading";

function ViewerLoading() {
  const t = useTranslations("PdfViewer");
  return (
    <div className="relative h-full w-full">
      <PdfViewerLoading label={t("loadingViewer")} />
    </div>
  );
}

const DocumentViewer = dynamic(
  () =>
    import("@/src/presentation/components/ui/document-viewer").then((mod) => ({
      default: mod.DocumentViewer,
    })),
  {
    ssr: false,
    loading: () => <ViewerLoading />,
  }
);

interface DocumentViewerPaneProps {
  document: WorkflowDocumentDetail;
  activeFieldKey?: string | null;
  onFieldSelect?: (fieldKey: string) => void;
}

export function DocumentViewerPane({
  document,
  activeFieldKey,
  onFieldSelect,
}: DocumentViewerPaneProps) {
  const accessToken = useSessionStore((s) => s.accessToken);
  const tenantSlug = useSessionStore((s) => s.tenant?.slug);
  const [fileProp, setFileProp] = useState<{
    url: string;
    httpHeaders: Record<string, string>;
  } | null>(null);

  const headers = useMemo(() => {
    const h: Record<string, string> = {};
    if (accessToken) h.Authorization = `Bearer ${accessToken}`;
    if (tenantSlug) h["X-Tenant"] = tenantSlug;
    return h;
  }, [accessToken, tenantSlug]);

  useEffect(() => {
    if (!document.fileId) return;
    setFileProp({
      url: `/api/v1/documents/${document.fileId}/download`,
      httpHeaders: headers,
    });
  }, [document.fileId, headers]);

  const pageOffset = (document.pageRange?.from ?? 1) - 1;
  const boxes = useMemo(
    () => mappedExtractionToBoxes(document.mappedExtraction, pageOffset),
    [document.mappedExtraction, pageOffset]
  );

  const activeBoxId = activeFieldKey ? fieldKeyToBoxId(activeFieldKey) : null;

  if (!fileProp) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Sin archivo asociado
      </div>
    );
  }

  return (
    <div className="border-r h-full w-full flex flex-col min-h-0">
      <DocumentViewer
        file={fileProp}
        mimeType={document.mimeType}
        fileName={document.fileName ?? undefined}
        initialPage={document.pageRange?.from}
        overlayBoxes={boxes}
        activeBoxId={activeBoxId}
        onBoxClick={(boxId) => {
          const match = boxId.match(/^field:([^:]+)/);
          if (match) onFieldSelect?.(match[1]);
        }}
        onLoadError={(error) => console.error("Error loading document:", error)}
      />
    </div>
  );
}
