"use client";

import { ChevronRight, ChevronDown } from "lucide-react";
import { useState } from "react";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { cn } from "@/src/application/lib/utils";
import { Badge } from "@/src/presentation/components/ui/badge";
import { TreeNodeActions } from "./tree-node-actions";

interface TreeNodeProps {
  name: string;
  path: string[];
  schema: JSONSchemaObject;
  selectedPath: string[];
  onSelect: (path: string[]) => void;
  onAddProperty: (parentPath: string[], propertyName: string) => void;
  onRemoveProperty: (path: string[]) => void;
  onToggleRequired: (parentPath: string[], propertyName: string) => void;
  isRequired?: boolean;
}

export function TreeNode({
  name,
  path,
  schema,
  selectedPath,
  onSelect,
  onAddProperty,
  onRemoveProperty,
  onToggleRequired,
  isRequired,
}: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const isSelected = JSON.stringify(path) === JSON.stringify(selectedPath);
  const hasChildren = schema.type === "object" && schema.properties;
  const isArray = schema.type === "array";

  const getTypeColor = (type: string | string[] | undefined) => {
    if (!type) return "default";
    const t = Array.isArray(type) ? type[0] : type;
    switch (t) {
      case "string":
        return "default";
      case "number":
      case "integer":
        return "secondary";
      case "boolean":
        return "outline";
      case "object":
        return "default";
      case "array":
        return "secondary";
      default:
        return "default";
    }
  };

  return (
    <div className="select-none">
      <div
        className={cn(
          "flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer hover:bg-muted/50 transition-colors group",
          isSelected && "bg-muted"
        )}
        onClick={() => onSelect(path)}
      >
        {hasChildren || isArray ? (
          <button
            className="flex-shrink-0 hover:bg-background rounded p-0.5"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <div className="w-5" />
        )}

        <span className="text-sm flex-1 font-mono">{name}</span>

        <Badge variant={getTypeColor(schema.type)} className="text-xs">
          {Array.isArray(schema.type)
            ? schema.type.join("|")
            : schema.type || "any"}
        </Badge>

        {isRequired && (
          <Badge variant="outline" className="text-xs">
            required
          </Badge>
        )}

        <TreeNodeActions
          path={path}
          schema={schema}
          onAddProperty={onAddProperty}
          onRemoveProperty={onRemoveProperty}
          onToggleRequired={onToggleRequired}
          isRequired={isRequired}
        />
      </div>

      {isExpanded && hasChildren && schema.properties && (
        <div className="ml-4 mt-1 border-l border-border/50 pl-2">
          {Object.entries(schema.properties).map(([key, childSchema]) => (
            <TreeNode
              key={key}
              name={key}
              path={[...path, key]}
              schema={childSchema}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onAddProperty={onAddProperty}
              onRemoveProperty={onRemoveProperty}
              onToggleRequired={onToggleRequired}
              isRequired={schema.required?.includes(key)}
            />
          ))}
        </div>
      )}

      {isExpanded && isArray && schema.items && (
        <div className="ml-4 mt-1 border-l border-border/50 pl-2">
          <TreeNode
            name="items"
            path={[...path, "items"]}
            schema={schema.items}
            selectedPath={selectedPath}
            onSelect={onSelect}
            onAddProperty={onAddProperty}
            onRemoveProperty={onRemoveProperty}
            onToggleRequired={onToggleRequired}
          />
        </div>
      )}
    </div>
  );
}
