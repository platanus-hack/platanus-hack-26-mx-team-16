"use client";

import { Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { authHttp } from "@/src/infrastructure/http/client";
import { Button } from "@/src/presentation/components/ui/button";

interface ImageSamplePreviewProps {
  fileId: string;
  fileName: string;
  onUploadClick?: () => void;
}

export function ImageSamplePreview({
  fileId,
  fileName,
  onUploadClick,
}: ImageSamplePreviewProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let created: string | null = null;

    authHttp
      .get(`/documents/${fileId}/download`, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        created = URL.createObjectURL(res.data as Blob);
        setBlobUrl(created);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la imagen");
      });

    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [fileId]);

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a]">
      <div className="flex items-center justify-between px-6 py-3.5 bg-[#2a2a2a] border-b border-[#3a3a3a]">
        <span className="text-sm text-gray-200 font-medium truncate">
          {fileName}
        </span>
        {onUploadClick && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onUploadClick}
            className="text-gray-200 hover:text-gray-100 hover:bg-[#3a3a3a] h-9 px-3"
          >
            <Upload className="h-5 w-5 mr-1.5" />
            Upload
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-auto bg-[#525659] flex items-center justify-center p-6">
        {error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : blobUrl ? (
          <img
            src={blobUrl}
            alt={fileName}
            className="max-w-full max-h-full object-contain shadow-2xl rounded-sm"
          />
        ) : (
          <p className="text-sm text-gray-300">Cargando imagen…</p>
        )}
      </div>
    </div>
  );
}
