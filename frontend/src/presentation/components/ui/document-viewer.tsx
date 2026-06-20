"use client";

import type { CoordinateBox } from "@/src/domain/entities/textract";
import { resolveFormat } from "@/src/application/lib/document-format";
import { PDFViewer } from "./pdf-viewer";
import { ImageViewer } from "./image-viewer";

export interface DocumentViewerProps {
  file: string | { url: string; httpHeaders?: Record<string, string> };
  mimeType?: string | null;
  fileName?: string;
  className?: string;
  showControls?: boolean;
  showZoom?: boolean;
  initialScale?: number;
  initialPage?: number;
  onLoadSuccess?: (numPages?: number) => void;
  onLoadError?: (error: Error) => void;
  onUploadClick?: () => void;
  overlayBoxes?: CoordinateBox[];
  activeBoxId?: string | null;
  onBoxClick?: (boxId: string) => void;
}

export function DocumentViewer({
  file,
  mimeType,
  fileName,
  className,
  showControls,
  showZoom,
  initialScale,
  initialPage,
  onLoadSuccess,
  onLoadError,
  onUploadClick,
  overlayBoxes,
  activeBoxId,
  onBoxClick,
}: DocumentViewerProps) {
  const url = typeof file === "string" ? file : file.url;
  const httpHeaders = typeof file === "string" ? undefined : file.httpHeaders;
  const format = resolveFormat(mimeType, fileName);

  if (format === "image") {
    return (
      <ImageViewer
        url={url}
        httpHeaders={httpHeaders}
        fileName={fileName}
        className={className}
        showControls={showControls}
        showZoom={showZoom}
        initialScale={initialScale}
        onLoadSuccess={() => onLoadSuccess?.()}
        onLoadError={onLoadError}
        overlayBoxes={overlayBoxes}
        activeBoxId={activeBoxId}
        onBoxClick={onBoxClick}
      />
    );
  }

  return (
    <PDFViewer
      file={file}
      fileName={fileName}
      className={className}
      showControls={showControls}
      showZoom={showZoom}
      initialScale={initialScale}
      initialPage={initialPage}
      onLoadSuccess={onLoadSuccess}
      onLoadError={onLoadError}
      onUploadClick={onUploadClick}
      overlayBoxes={overlayBoxes}
      activeBoxId={activeBoxId}
      onBoxClick={onBoxClick}
    />
  );
}
