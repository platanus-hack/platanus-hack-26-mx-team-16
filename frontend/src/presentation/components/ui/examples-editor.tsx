"use client";

import { Plus, Trash2 } from "lucide-react";
import { cn } from "@/src/application/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";
import { MarkdownRichEditor } from "@/src/presentation/components/ui/markdown-rich-editor";

interface ExamplesEditorProps {
  value: string[];
  onChange: (next: string[]) => void;
  className?: string;
}

export function ExamplesEditor({
  value,
  onChange,
  className,
}: ExamplesEditorProps) {
  const updateAt = (idx: number, next: string) => {
    onChange(value.map((v, i) => (i === idx ? next : v)));
  };

  const removeAt = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  const addExample = () => {
    onChange([...value, ""]);
  };

  return (
    <div className={cn("space-y-3", className)}>
      {value.map((example, idx) => (
        <div key={idx} className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Example #{idx + 1}
            </span>
            <button
              type="button"
              onClick={() => removeAt(idx)}
              className="rounded p-1 text-muted-foreground/60 hover:text-destructive hover:bg-destructive/10 cursor-pointer"
              aria-label={`Remove example ${idx + 1}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
          <MarkdownRichEditor
            value={example}
            onChange={(next) => updateAt(idx, next)}
            placeholder="Write an example…"
            minHeight={120}
          />
        </div>
      ))}
      <Button
        variant="ghost"
        size="sm"
        className="gap-2 p-0 h-auto text-sm text-primary hover:underline hover:bg-transparent"
        onClick={addExample}
      >
        <Plus className="h-4 w-4" />
        Add Example
      </Button>
    </div>
  );
}
