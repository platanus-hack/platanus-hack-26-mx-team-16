"use client";

import { Upload } from "lucide-react";
import { Spinner } from "@/src/presentation/components/ui/spinner";
import { useRef, useState } from "react";

import { authHttp } from "@/src/infrastructure/http/client";

interface DocumentUploadButtonProps {
  workflowId: string;
  /** ANALYSIS workflows pass this; STANDARD workflows do not. */
  workflowCaseId?: string;
  /** Called once per dispatched file so the parent can refresh state. */
  onDispatched?: (setId: string) => void;
  disabled?: boolean;
  label?: string;
  accept?: string;
  /** Subtle outline style for in-row affordances (vs the prominent toolbar CTA). */
  compact?: boolean;
}

interface UploadFileResponse {
  data: { uuid: string; s3Key: string };
}

interface DispatchResponse {
  data: {
    setId: string;
    temporalWorkflowId: string;
    status: string;
  };
}

interface UploadProgress {
  current: number;
  total: number;
}

const DEFAULT_ACCEPT = "application/pdf,image/jpeg,image/jpg,image/png";
const DEFAULT_LABEL = "Cargar documento";

export function FileUploadButton({
  workflowId,
  workflowCaseId,
  onDispatched,
  disabled,
  label = DEFAULT_LABEL,
  accept = DEFAULT_ACCEPT,
  compact = false,
}: DocumentUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);

  async function uploadAndDispatch(file: File): Promise<string | null> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const uploadRes = await authHttp.post<UploadFileResponse>(
        "/v1/documents/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      const fileId = uploadRes.data.data.uuid;

      const dispatchRes = await authHttp.post<DispatchResponse>(
        `/v1/workflows/${workflowId}/jobs`,
        { fileId, workflowCaseId },
      );
      return dispatchRes.data.data.setId;
    } catch (err) {
      // One bad file shouldn't stop the rest of the batch — log and
      // continue. The parent gets a callback per success.
      console.error(`file-upload failed for "${file.name}":`, err);
      return null;
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    const total = files.length;

    setProgress({ current: 0, total });
    try {
      for (let i = 0; i < files.length; i++) {
        setProgress({ current: i + 1, total });
        const setId = await uploadAndDispatch(files[i]);
        if (setId) onDispatched?.(setId);
      }
    } finally {
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const isUploading = progress !== null;
  const buttonLabel = isUploading
    ? progress.total > 1
      ? `Cargando ${progress.current}/${progress.total}`
      : "Subiendo…"
    : label;

  const className = compact
    ? `inline-flex items-center gap-1.5 cursor-pointer rounded-md border border-border
       bg-background text-foreground px-2.5 py-1.5 text-xs font-medium transition-colors
       hover:bg-accent hover:text-accent-foreground
       disabled:opacity-50 disabled:cursor-not-allowed`
    : `inline-flex items-center gap-2 cursor-pointer rounded-md border border-border
       bg-foreground text-background px-4 py-2 text-sm font-medium shadow-sm transition-all
       hover:shadow-md hover:-translate-y-px
       disabled:opacity-50 disabled:cursor-not-allowed disabled:translate-y-0`;

  return (
    <button
      type="button"
      onClick={() => inputRef.current?.click()}
      disabled={isUploading || disabled}
      className={className}
    >
      {isUploading ? (
        <Spinner size="sm" />
      ) : (
        <Upload className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} aria-hidden />
      )}
      <span className="tabular-nums">{buttonLabel}</span>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleFileChange}
        className="hidden"
      />
    </button>
  );
}
