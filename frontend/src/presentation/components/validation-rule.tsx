"use client";

import type { ReactNode } from "react";
import { GripVertical, Trash2 } from "lucide-react";
import { ValidationRule as ValidationRuleType } from "@/src/domain/entities/doctype";
import { BaseListRow } from "@/src/presentation/components/common/base-list-row";
import { Switch } from "@/src/presentation/components/ui/switch";

interface ValidationRuleProps {
  rule: ValidationRuleType;
  onToggle?: (enabled: boolean) => void;
  onClick?: () => void;
  onDelete?: () => void;
  dragHandleProps?: React.HTMLAttributes<HTMLDivElement>;
  label?: ReactNode;
  className?: string;
}

export function ValidationRule({
  rule,
  onToggle,
  onClick,
  onDelete,
  dragHandleProps,
  label,
  className,
}: ValidationRuleProps) {
  return (
    <BaseListRow
      onClick={onClick}
      className={`cursor-pointer ${className ?? ""}`}
    >
      <div
        {...dragHandleProps}
        className="shrink-0 cursor-grab active:cursor-grabbing text-muted-foreground/50 hover:text-muted-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0 self-center text-sm leading-snug">
        {label ?? <span className="line-clamp-2">{rule.name}</span>}
      </div>

      <div
        className="shrink-0 flex items-center gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <Switch checked={rule.enabled} onCheckedChange={onToggle} />
        {onDelete && (
          <button
            type="button"
            aria-label="Eliminar regla"
            onClick={onDelete}
            className="rounded p-1 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </BaseListRow>
  );
}
