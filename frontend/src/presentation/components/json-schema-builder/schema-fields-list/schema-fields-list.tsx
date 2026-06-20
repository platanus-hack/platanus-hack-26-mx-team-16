"use client";

import { Plus } from "lucide-react";
import { useCallback, useState, type DragEvent } from "react";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { SchemaFieldRow } from "./schema-field-row";
import type { SchemaFieldsCallbacks } from "./types";

interface SchemaFieldsListProps extends SchemaFieldsCallbacks {
  parentSchema: JSONSchemaObject;
  parentPath: string[];
  depth: number;
  /** When the list is rendered as nested children, the parent's `required` set is passed in. */
  requiredFromParent?: Set<string>;
}

const NEW_FIELD_PREFIX = "field";

function generateUniqueName(
  existing: string[],
  prefix = NEW_FIELD_PREFIX
): string {
  if (!existing.includes(prefix)) return prefix;
  let i = 2;
  while (existing.includes(`${prefix}${i}`)) i++;
  return `${prefix}${i}`;
}

export function SchemaFieldsList(props: SchemaFieldsListProps) {
  const {
    parentSchema,
    parentPath,
    depth,
    requiredFromParent,
    onAdd,
    onRename,
    onReplace,
    onDescriptionChange,
    onToggleRequired,
    onDelete,
    onReorder,
  } = props;

  const callbacks: SchemaFieldsCallbacks = {
    onAdd,
    onRename,
    onReplace,
    onDescriptionChange,
    onToggleRequired,
    onDelete,
    onReorder,
  };

  const properties = parentSchema.properties ?? {};
  const propertyNames = Object.keys(properties);
  const requiredSet =
    requiredFromParent ?? new Set(parentSchema.required ?? []);

  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleDragStart = useCallback(
    (idx: number) => (e: DragEvent) => {
      setDraggedIndex(idx);
      e.dataTransfer.effectAllowed = "move";
    },
    []
  );

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const handleDrop = useCallback(
    (idx: number) => (e: DragEvent) => {
      e.preventDefault();
      if (draggedIndex === null || draggedIndex === idx) return;
      onReorder(parentPath, draggedIndex, idx);
      setDraggedIndex(null);
    },
    [draggedIndex, onReorder, parentPath]
  );

  const handleAdd = useCallback(() => {
    onAdd(parentPath, generateUniqueName(propertyNames), "string");
  }, [onAdd, parentPath, propertyNames]);

  const isRoot = depth === 0;

  return (
    <div className={isRoot ? "space-y-1.5" : "space-y-1"}>
      {propertyNames.map((propName, idx) => (
        <SchemaFieldRow
          key={propName}
          name={propName}
          schema={properties[propName]}
          parentPath={parentPath}
          isRequired={requiredSet.has(propName)}
          depth={depth}
          isDraggable={isRoot}
          onDragStart={isRoot ? handleDragStart(idx) : undefined}
          onDragOver={isRoot ? handleDragOver : undefined}
          onDrop={isRoot ? handleDrop(idx) : undefined}
          {...callbacks}
        />
      ))}

      <div className="pt-1">
        <button
          type="button"
          onClick={handleAdd}
          className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted/50"
        >
          <Plus className="h-3 w-3" />
          {isRoot ? "Agregar campo" : "Agregar campo anidado"}
        </button>
      </div>
    </div>
  );
}
