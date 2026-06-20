"use client";

import type {
  JSONSchemaObject,
  JSONSchemaType,
} from "@/src/domain/entities/json-schema";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { Textarea } from "@/src/presentation/components/ui/textarea";
import { ScrollArea } from "@/src/presentation/components/ui/scroll-area";
import { Separator } from "@/src/presentation/components/ui/separator";
import { TypeSelector } from "./type-selector";
import { StringConstraints } from "./string-constraints";
import { NumberConstraints } from "./number-constraints";
import { ArrayConstraints } from "./array-constraints";
import { ObjectConstraints } from "./object-constraints";

interface PropertyEditorProps {
  schema: JSONSchemaObject | undefined;
  path: string[];
  onChange: (updates: Partial<JSONSchemaObject>) => void;
}

export function PropertyEditor({
  schema,
  path,
  onChange,
}: PropertyEditorProps) {
  if (!schema) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Select a property to edit
      </div>
    );
  }

  const handleTypeChange = (type: JSONSchemaType) => {
    onChange({ type });
  };

  const currentType = Array.isArray(schema.type) ? schema.type[0] : schema.type;

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-1">
            {path.length > 0 ? path[path.length - 1] : "root"}
          </h3>
          <p className="text-sm text-muted-foreground">
            {path.length > 0 ? path.join(" > ") : "Root schema"}
          </p>
        </div>

        <Separator />

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              value={schema.title ?? ""}
              onChange={(e) => onChange({ title: e.target.value || undefined })}
              placeholder="Property title"
            />
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={schema.description ?? ""}
              onChange={(e) =>
                onChange({ description: e.target.value || undefined })
              }
              placeholder="Property description"
              rows={3}
            />
          </div>
        </div>

        <Separator />

        <TypeSelector value={schema.type} onChange={handleTypeChange} />

        {currentType && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-4">Constraints</h4>
              {currentType === "string" && (
                <StringConstraints schema={schema} onChange={onChange} />
              )}
              {(currentType === "number" || currentType === "integer") && (
                <NumberConstraints schema={schema} onChange={onChange} />
              )}
              {currentType === "array" && (
                <ArrayConstraints schema={schema} onChange={onChange} />
              )}
              {currentType === "object" && (
                <ObjectConstraints schema={schema} onChange={onChange} />
              )}
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}
