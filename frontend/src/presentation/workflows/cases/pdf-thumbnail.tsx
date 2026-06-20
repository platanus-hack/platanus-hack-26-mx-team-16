"use client";

import { useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { FileText } from "lucide-react";
import { Spinner } from "@/src/presentation/components/ui/spinner";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

if (typeof window !== "undefined" && !pdfjs.GlobalWorkerOptions.workerSrc) {
  pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface PdfThumbnailProps {
  data: Uint8Array;
  height?: number;
}

export function PdfThumbnail({ data, height = 140 }: PdfThumbnailProps) {
  const file = useMemo(() => ({ data }), [data]);
  const options = useMemo(
    () => ({ disableStream: true, disableAutoFetch: true, disableRange: true }),
    []
  );

  return (
    <Document
      file={file}
      options={options}
      loading={<Spinner size="sm" variant="muted" />}
      error={<FileText className="h-12 w-12 text-muted-foreground/40" />}
    >
      <Page
        pageNumber={1}
        height={height}
        renderAnnotationLayer={false}
        renderTextLayer={false}
      />
    </Document>
  );
}
