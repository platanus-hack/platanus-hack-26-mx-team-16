"use client";

import { ChevronDown, ChevronRight, GripVertical, Trash2 } from "lucide-react";
import { useState, type DragEvent } from "react";
import { cn } from "@/src/application/lib/utils";
import type {
  JSONSchemaObject,
  JSONSchemaType,
} from "@/src/domain/entities/json-schema";
import { SchemaFieldsList } from "./schema-fields-list";
import type { SchemaFieldsCallbacks } from "./types";

const TYPE_OPTIONS: { value: JSONSchemaType; label: string }[] = [
  { value: "string", label: "Texto" },
  { value: "number", label: "Número" },
  { value: "integer", label: "Entero" },
  { value: "boolean", label: "Booleano" },
  { value: "object", label: "Objeto" },
  { value: "array", label: "Lista" },
];

const SELECT_CHEVRON_BG =
  "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23888%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22%2F%3E%3C%2Fsvg%3E')] bg-no-repeat bg-[right_0.5rem_center]";

export interface SchemaFieldRowProps extends SchemaFieldsCallbacks {
  name: string;
  schema: JSONSchemaObject;
  parentPath: string[];
  isRequired: boolean;
  depth: number;
  isDraggable: boolean;
  onDragStart?: (e: DragEvent) => void;
  onDragOver?: (e: DragEvent) => void;
  onDrop?: (e: DragEvent) => void;
}

export function SchemaFieldRow(props: SchemaFieldRowProps) {
  const {
    name,
    schema,
    parentPath,
    isRequired,
    depth,
    isDraggable,
    onDragStart,
    onDragOver,
    onDrop,
    onAdd,
    onRename,
    onReplace,
    onDescriptionChange,
    onToggleRequired,
    onDelete,
    onReorder,
  } = props;

  const currentType =
    (Array.isArray(schema.type) ? schema.type[0] : schema.type) ?? "string";
  const isObjectType = currentType === "object";
  const [expanded, setExpanded] = useState(true);
  const [draftName, setDraftName] = useState(name);

  const ownPath = [...parentPath, name];

  const commitRename = () => {
    const trimmed = draftName.trim();
    if (!trimmed || trimmed === name) {
      setDraftName(name);
      return;
    }
    onRename(parentPath, name, trimmed);
  };

  const handleTypeChange = (next: JSONSchemaType) => {
    const replacement: JSONSchemaObject = {
      type: next,
      ...(schema.title ? { title: schema.title } : {}),
      ...(schema.description ? { description: schema.description } : {}),
    };
    if (next === "object") {
      replacement.properties =
        currentType === "object" ? (schema.properties ?? {}) : {};
    } else if (next === "array") {
      replacement.items =
        currentType === "array"
          ? (schema.items ?? { type: "string" })
          : { type: "string" };
    }
    onReplace(ownPath, replacement);
  };

  const requiredSet = new Set(schema.required ?? []);

  return (
    <div>
      <div
        draggable={isDraggable}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDrop={onDrop}
        className={cn(
          "group flex flex-wrap items-center gap-x-1.5 gap-y-2 rounded-lg border bg-background px-2 py-3 transition-colors",
          depth === 0 ? "border-border" : "border-border/60",
          isDraggable && "cursor-move"
        )}
      >
        {isDraggable && depth === 0 && (
          <div className="shrink-0 cursor-grab text-muted-foreground/40 hover:text-muted-foreground/70 active:cursor-grabbing">
            <GripVertical className="h-4 w-4" />
          </div>
        )}

        {isObjectType ? (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="shrink-0 cursor-pointer rounded p-0.5 hover:bg-muted"
            aria-label={expanded ? "Colapsar" : "Expandir"}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        ) : null}

        <input
          type="text"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.currentTarget.blur();
            } else if (e.key === "Escape") {
              setDraftName(name);
              e.currentTarget.blur();
            }
          }}
          placeholder="key"
          className="w-28 min-w-0 shrink-0 rounded-md border border-transparent bg-muted/60 px-2.5 py-1 font-mono text-sm outline-none placeholder:text-muted-foreground/40 focus:border-primary/40"
        />

        <input
          type="text"
          value={schema.description ?? ""}
          onChange={(e) =>
            onDescriptionChange(ownPath, e.target.value || undefined)
          }
          placeholder="Descripción"
          className="min-w-[140px] flex-1 basis-40 border-b border-transparent bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground/40 focus:border-primary/40"
        />

        <select
          value={currentType}
          onChange={(e) => handleTypeChange(e.target.value as JSONSchemaType)}
          className={cn(
            "shrink-0 cursor-pointer appearance-none rounded-md border border-border bg-background px-3 py-1.5 pr-7 text-sm outline-none hover:bg-muted/50 focus:border-primary/40",
            SELECT_CHEVRON_BG
          )}
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => onToggleRequired(parentPath, name)}
          className={cn(
            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors",
            isRequired ? "bg-primary" : "bg-muted-foreground/20"
          )}
          aria-label={
            isRequired ? "Marcar como opcional" : "Marcar como requerido"
          }
          title={isRequired ? "Requerido" : "Opcional"}
        >
          <span
            className={cn(
              "inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform",
              isRequired ? "translate-x-4.5" : "translate-x-0.5"
            )}
          />
        </button>

        <button
          type="button"
          onClick={() => onDelete(ownPath)}
          className="shrink-0 cursor-pointer rounded p-1 text-muted-foreground/40 transition-all hover:bg-destructive/10 hover:text-destructive"
          aria-label="Eliminar campo"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {isObjectType && expanded && (
        <div className="mt-1" style={{ marginLeft: 28 }}>
          <SchemaFieldsList
            parentSchema={schema}
            parentPath={ownPath}
            depth={depth + 1}
            onAdd={onAdd}
            onRename={onRename}
            onReplace={onReplace}
            onDescriptionChange={onDescriptionChange}
            onToggleRequired={onToggleRequired}
            onDelete={onDelete}
            onReorder={onReorder}
            requiredFromParent={requiredSet}
          />
        </div>
      )}
    </div>
  );
}
