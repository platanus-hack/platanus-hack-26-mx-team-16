"use client";

import { FileUp, Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DocumentType } from "src/domain/entities/doctype";
import { useSessionStore } from "src/application/contexts/session-store";
import { authHttp } from "src/infrastructure/http/client";
import { HttpDocumentRepository } from "src/infrastructure/repositories/http-document";
import { Button } from "src/presentation/components/ui/button";
import { ActionButton } from "src/presentation/components/ui/action-button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "src/presentation/components/ui/sheet";
import { DocumentTypeConfigPanel } from "./doctype-config";
import { ConfirmReplaceDocumentDialog } from "../detail/confirm-replace-document-dialog";
import { DocumentUploadArea } from "../detail/document-upload-area";
import { ImageSamplePreview } from "../detail/image-sample-preview";
import { PdfViewerLoading } from "src/presentation/components/ui/pdf-viewer-loading";

const PDFViewer = dynamic(
  () =>
    import("src/presentation/components/ui/pdf-viewer").then((mod) => ({
      default: mod.PDFViewer,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="relative h-full w-full">
        <PdfViewerLoading />
      </div>
    ),
  }
);

interface DocumentTypePreviewPaneProps {
  doctype: DocumentType;
  onUpdate: () => void;
  onSampleFileUploaded?: () => void;
}

export function DocumentTypePreviewPanel({
  doctype,
  onUpdate,
  onSampleFileUploaded,
}: DocumentTypePreviewPaneProps) {
  const t = useTranslations("DoctypePreview");
  const [isMetadataOpen, setIsMetadataOpen] = useState(false);
  const [showUploadArea, setShowUploadArea] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [confirmReplaceOpen, setConfirmReplaceOpen] = useState(false);
  const [selectedPdf, setSelectedPdf] = useState<
    string | { url: string; httpHeaders: Record<string, string> } | null
  >(null);
  const [fileName, setFileName] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [localSampleFileId, setLocalSampleFileId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentSampleFileId = localSampleFileId ?? doctype.sampleFileId;
  const hasSampleDocument = !!currentSampleFileId;

  // Load sample document via download proxy (avoids S3 CORS issues)
  const accessToken = useSessionStore((s) => s.accessToken);
  const tenantSlug = useSessionStore((s) => s.tenant?.slug);

  useEffect(() => {
    const documentRepository = new HttpDocumentRepository(authHttp);
    if (doctype.sampleFileId) {
      documentRepository
        .getById(doctype.sampleFileId)
        .then((res) => {
          if (!("data" in res)) return;
          const headers: Record<string, string> = {};
          if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
          if (tenantSlug) headers["X-Tenant"] = tenantSlug;
          setSelectedPdf({
            url: `/api/v1/documents/${doctype.sampleFileId}/download`,
            httpHeaders: headers,
          });
          setFileName(res.data.name || "document.pdf");
        })
        .catch((err) => {
          console.error("Failed to load sample document:", err);
        });
    } else if (doctype.referenceDocumentUrl) {
      setSelectedPdf(doctype.referenceDocumentUrl);
      setFileName(
        doctype.referenceDocumentUrl.split("/").pop() || "document.pdf"
      );
    }
  }, [
    doctype.sampleFileId,
    doctype.referenceDocumentUrl,
    accessToken,
    tenantSlug,
  ]);

  const handleFileUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      try {
        // Upload to S3 via existing endpoint
        const formData = new FormData();
        formData.append("file", file);
        const uploadRes = await authHttp.post("/v1/documents/upload", formData);
        const uploadedFile = uploadRes.data?.data;
        if (!uploadedFile?.uuid) return;

        // Update document type with sample_file_id
        await authHttp.put(`/v1/document-types/${doctype.uuid}`, {
          sampleFileId: uploadedFile.uuid,
        });

        // Get presigned URL and display
        const fileRes = await authHttp.get(
          `/v1/documents/${uploadedFile.uuid}`
        );
        const fileData = fileRes.data?.data;
        if (fileData?.presignedUrl) {
          setSelectedPdf(fileData.presignedUrl);
          setFileName(fileData.fileName || file.name);
          setLocalSampleFileId(uploadedFile.uuid);
        }

        setShowUploadArea(false);
        onUpdate();
        onSampleFileUploaded?.();
      } catch (err) {
        console.error("Failed to upload sample document:", err);
      } finally {
        setIsUploading(false);
      }
    },
    [doctype.uuid, onUpdate, onSampleFileUploaded]
  );

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelectWithConfirm(file);
  };

  const hasExistingData =
    Boolean(currentSampleFileId) ||
    Boolean(doctype.fields && Object.keys(doctype.fields).length > 0);

  const handleFileSelectWithConfirm = (file: File) => {
    if (hasExistingData) {
      setPendingFile(file);
      setConfirmReplaceOpen(true);
    } else {
      void handleFileUpload(file);
    }
  };

  // No sample document - show empty state
  if (!hasSampleDocument && !selectedPdf && !showUploadArea) {
    return (
      <>
        <div className="md:col-span-2 bg-muted/30 h-full min-h-0 relative flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-center p-8">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <FileUp className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold">{t("emptyTitle")}</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                {t("emptyDescription")}
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp"
              onChange={handleFileInputChange}
              className="hidden"
            />
            <ActionButton
              onClick={() => fileInputRef.current?.click()}
              disabled={confirmReplaceOpen}
              loading={isUploading}
              icon={<FileUp className="h-4 w-4" />}
              className="gap-2"
            >
              {isUploading ? t("uploading") : t("upload")}
            </ActionButton>
          </div>
        </div>

        <Sheet open={isMetadataOpen} onOpenChange={setIsMetadataOpen}>
          <SheetContent side="left" className="w-[95%] sm:w-[400px] p-0">
            <SheetHeader className="px-4 py-3 border-b">
              <SheetTitle>{t("configSheetTitle")}</SheetTitle>
            </SheetHeader>
            <div className="h-[calc(100vh-60px)]">
              <DocumentTypeConfigPanel doctype={doctype} onUpdate={onUpdate} />
            </div>
          </SheetContent>
        </Sheet>
        <ConfirmReplaceDocumentDialog
          open={confirmReplaceOpen}
          onOpenChange={setConfirmReplaceOpen}
          hasFields={Boolean(
            doctype.fields && Object.keys(doctype.fields).length > 0
          )}
          hasExtractedText={Boolean(doctype.sampleFileText)}
          onConfirm={() => {
            if (pendingFile) void handleFileUpload(pendingFile);
            setPendingFile(null);
          }}
        />
      </>
    );
  }

  return (
    <>
      <div className="md:col-span-2 bg-muted/30 h-full min-h-0 relative">
        {/* Mobile toggle button */}
        <Button
          variant="outline"
          size="icon"
          className="md:hidden absolute top-4 left-4 z-10"
          onClick={() => setIsMetadataOpen(true)}
        >
          <Menu className="h-4 w-4" />
        </Button>

        {!showUploadArea && selectedPdf ? (
          /\.(png|jpe?g|gif|webp|tiff?|bmp|svg)$/i.test(fileName) &&
          currentSampleFileId ? (
            <ImageSamplePreview
              fileId={currentSampleFileId}
              fileName={fileName}
              onUploadClick={() => setShowUploadArea(true)}
            />
          ) : (
            <PDFViewer
              file={selectedPdf}
              fileName={fileName}
              onUploadClick={() => setShowUploadArea(true)}
              onLoadError={(error) => {
                console.error("Error loading PDF:", error);
              }}
            />
          )
        ) : (
          <DocumentUploadArea
            onFileSelect={handleFileSelectWithConfirm}
            onCancel={() => setShowUploadArea(false)}
          />
        )}
      </div>

      <Sheet open={isMetadataOpen} onOpenChange={setIsMetadataOpen}>
        <SheetContent side="left" className="w-[95%] sm:w-[400px] p-0">
          <SheetHeader className="px-4 py-3 border-b">
            <SheetTitle>Document Type Configuration</SheetTitle>
          </SheetHeader>
          <div className="h-[calc(100vh-60px)]">
            <DocumentTypeConfigPanel doctype={doctype} onUpdate={onUpdate} />
          </div>
        </SheetContent>
      </Sheet>
      <ConfirmReplaceDocumentDialog
        open={confirmReplaceOpen}
        onOpenChange={setConfirmReplaceOpen}
        hasFields={Boolean(
          doctype.fields && Object.keys(doctype.fields).length > 0
        )}
        hasExtractedText={Boolean(doctype.sampleFileText)}
        onConfirm={() => {
          if (pendingFile) void handleFileUpload(pendingFile);
          setPendingFile(null);
        }}
      />
    </>
  );
}
