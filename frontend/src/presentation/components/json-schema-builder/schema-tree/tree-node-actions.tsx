"use client";

import { Plus, Trash2, MoreVertical } from "lucide-react";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Button } from "@/src/presentation/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";

interface TreeNodeActionsProps {
  path: string[];
  schema: JSONSchemaObject;
  onAddProperty: (parentPath: string[], propertyName: string) => void;
  onRemoveProperty: (path: string[]) => void;
  onToggleRequired: (parentPath: string[], propertyName: string) => void;
  isRequired?: boolean;
}

export function TreeNodeActions({
  path,
  schema,
  onAddProperty,
  onRemoveProperty,
  onToggleRequired,
  isRequired,
}: TreeNodeActionsProps) {
  const canAddProperty = schema.type === "object";
  const canDelete = path.length > 0;
  const canToggleRequired = path.length > 0;

  const handleAddProperty = (e: React.MouseEvent) => {
    e.stopPropagation();
    const propertyName = `property${Object.keys(schema.properties || {}).length + 1}`;
    onAddProperty(path, propertyName);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemoveProperty(path);
  };

  const handleToggleRequired = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (path.length > 0) {
      const parentPath = path.slice(0, -1);
      const propertyName = path[path.length - 1];
      onToggleRequired(parentPath, propertyName);
    }
  };

  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {canAddProperty && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={handleAddProperty}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      )}

      {(canDelete || canToggleRequired) && (
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {canToggleRequired && (
              <DropdownMenuItem onClick={handleToggleRequired}>
                {isRequired ? "Mark as optional" : "Mark as required"}
              </DropdownMenuItem>
            )}
            {canDelete && (
              <DropdownMenuItem
                onClick={handleDelete}
                className="text-destructive"
              >
                Delete property
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
