"use client";

import { FileText, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { cn } from "@/src/application/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";

interface DocumentUploadAreaProps {
  onFileSelect?: (file: File) => void;
  onCancel?: () => void;
}

export function DocumentUploadArea({
  onFileSelect,
  onCancel,
}: DocumentUploadAreaProps) {
  const t = useTranslations("DocumentUploadArea");
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && files[0].type === "application/pdf") {
      onFileSelect?.(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect?.(files[0]);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="p-8 flex flex-col items-center justify-center h-full relative"
    >
      {onCancel && (
        <Button
          variant="ghost"
          size="icon-sm"
          className="absolute top-4 right-4"
          onClick={onCancel}
        >
          <X className="h-4 w-4" />
        </Button>
      )}

      <div
        className={cn(
          "w-full h-full flex flex-col items-center justify-center gap-6 transition-opacity min-h-[500px]",
          isDragOver ? "opacity-70" : ""
        )}
      >
        <div className="flex items-center justify-center">
          <FileText className="h-16 w-16 text-muted-foreground/60" />
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-lg font-medium">{t("title")}</h3>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>

        <p className="text-sm text-muted-foreground">{t("dragHint")}</p>

        <label htmlFor="file-upload">
          <Button
            type="button"
            className="gap-2"
            onClick={() => document.getElementById("file-upload")?.click()}
          >
            {t("chooseFile")}
          </Button>
          <input
            id="file-upload"
            type="file"
            className="hidden"
            accept=".pdf"
            onChange={handleFileSelect}
          />
        </label>
      </div>
    </div>
  );
}
