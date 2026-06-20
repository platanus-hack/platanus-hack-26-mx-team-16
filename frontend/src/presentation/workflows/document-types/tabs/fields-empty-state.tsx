"use client";

import { AlertCircle, AlignLeft, FileJson, Plus, Sparkles } from "lucide-react";
import { Button } from "src/presentation/components/ui/button";

interface DocumentTypeFieldsEmptyStateProps {
  hasSampleDocument: boolean;
  importError: string | null;
  onAddField: () => void;
  onImportClick: () => void;
}

export function DocumentTypeFieldsEmptyState({
  hasSampleDocument,
  importError,
  onAddField,
  onImportClick,
}: DocumentTypeFieldsEmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center max-w-md px-4">
      <div className="mb-6 rounded-full bg-muted/50 p-8">
        <AlignLeft className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">Define your fields</h3>
      <p className="text-sm text-muted-foreground mb-6">
        Add fields to describe the data you want to extract from documents.
      </p>
      <div className="flex items-center gap-2 w-full">
        <Button onClick={onAddField} className="gap-2 flex-1">
          <Plus className="h-4 w-4" />
          Add Field
        </Button>
        <Button
          variant="outline"
          onClick={onImportClick}
          className="gap-2 flex-1"
        >
          <FileJson className="h-4 w-4" />
          Import JSON
        </Button>
        <Button
          variant="outline"
          onClick={() => {}}
          className="gap-2 flex-1"
          disabled={!hasSampleDocument}
        >
          <Sparkles className="h-4 w-4" />
          Suggest Fields
        </Button>
      </div>
      {importError && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-left text-xs text-destructive"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{importError}</span>
        </div>
      )}
    </div>
  );
}
