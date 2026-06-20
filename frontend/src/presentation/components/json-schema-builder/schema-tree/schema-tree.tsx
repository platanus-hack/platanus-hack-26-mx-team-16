"use client";

import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { TreeNode } from "./tree-node";
import { ScrollArea } from "@/src/presentation/components/ui/scroll-area";

interface SchemaTreeProps {
  schema: JSONSchemaObject;
  selectedPath: string[];
  onSelect: (path: string[]) => void;
  onAddProperty: (parentPath: string[], propertyName: string) => void;
  onRemoveProperty: (path: string[]) => void;
  onToggleRequired: (parentPath: string[], propertyName: string) => void;
}

export function SchemaTree({
  schema,
  selectedPath,
  onSelect,
  onAddProperty,
  onRemoveProperty,
  onToggleRequired,
}: SchemaTreeProps) {
  return (
    <ScrollArea className="h-full">
      <div className="p-4">
        <TreeNode
          name="root"
          path={[]}
          schema={schema}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onAddProperty={onAddProperty}
          onRemoveProperty={onRemoveProperty}
          onToggleRequired={onToggleRequired}
        />
      </div>
    </ScrollArea>
  );
}
