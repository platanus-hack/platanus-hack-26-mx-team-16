"use client";

import { Upload } from "lucide-react";
import { Spinner } from "src/presentation/components/ui/spinner";
import { useRef, useState } from "react";
import type { DocumentType } from "src/domain/entities/doctype";
import { authHttp } from "src/infrastructure/http/client";

interface DocumentTypeCardProps {
  workflowUuid: string;
  caseId: string;
  documentType: DocumentType;
  document: null;
  onDocumentsChanged: () => Promise<void>;
}

interface UploadFileResponse {
  data: { uuid: string; s3Key: string };
}

interface DispatchResponse {
  data: { setId: string; temporalWorkflowId: string; status: string };
}

export function DocumentTypeCard({
  workflowUuid,
  caseId,
  documentType,
  onDocumentsChanged,
}: DocumentTypeCardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Same flow as `DocumentUploadButton` (the toolbar's "Cargar documento"):
  // upload to /v1/documents/upload, then dispatch a processing-job against
  // the unified endpoint. The Temporal workflow drives the live feed and
  // persists the resulting WorkflowDocuments — we don't pre-attach the
  // document_type because classify_pages decides where each page goes (a
  // single PDF can contain N logical doc types).
  const handleFileSelect = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const uploadRes = await authHttp.post<UploadFileResponse>(
        "/v1/documents/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      const fileId = uploadRes.data.data.uuid;

      await authHttp.post<DispatchResponse>(
        `/v1/workflows/${workflowUuid}/jobs`,
        { fileId, workflowCaseId: caseId }
      );
      await onDocumentsChanged();
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) handleFileSelect(files[0]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <div className="rounded-xl border bg-card p-5 flex flex-col gap-3">
      <div className="min-w-0">
        <h3 className="font-semibold text-base">{documentType.name}</h3>
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
          {documentType.description || "---"}
        </p>
      </div>

      <input
        ref={fileInputRef}
        id={`doc-upload-${documentType.uuid}`}
        type="file"
        className="sr-only"
        accept="application/pdf,image/jpeg,image/jpg,image/png"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFileSelect(f);
        }}
      />

      <label
        htmlFor={`doc-upload-${documentType.uuid}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        aria-disabled={isUploading}
        className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-muted-foreground/25 py-8 text-muted-foreground hover:border-muted-foreground/40 hover:bg-muted/30 transition-colors cursor-pointer ${
          isUploading ? "opacity-50 pointer-events-none" : ""
        }`}
      >
        {isUploading ? <Spinner size="md" /> : <Upload className="h-6 w-6" />}
        <span className="text-sm">
          {isUploading ? "Subiendo..." : "Arrastra o haz clic para subir"}
        </span>
      </label>
    </div>
  );
}
