"use client";

import { ChevronDown, ChevronRight, GripVertical, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import {
  type DocumentTypeField,
  FieldType,
} from "@/src/domain/entities/doctype";
import { BaseListRow } from "@/src/presentation/components/common/base-list-row";
import { FIELD_TYPE_META } from "@/src/presentation/components/field-type-meta";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

interface DocumentTypeFieldRowProps {
  field: DocumentTypeField;
  depth?: number;
  expandable?: boolean;
  expanded?: boolean;
  isArrayItem?: boolean;
  onToggleExpand?: () => void;
  onClick?: () => void;
  onToggleEnabled?: (enabled: boolean) => void;
  onTypeChange?: (type: FieldType) => void;
  onDelete?: () => void;
  dragHandleProps?: React.HTMLAttributes<HTMLDivElement>;
  isDraggable?: boolean;
  className?: string;
}

export function DocumentTypeFieldRow({
  field,
  depth = 0,
  expandable = false,
  expanded = false,
  isArrayItem = false,
  onToggleExpand,
  onClick,
  onToggleEnabled,
  onTypeChange,
  onDelete,
  dragHandleProps,
  isDraggable = false,
  className,
}: DocumentTypeFieldRowProps) {
  const t = useTranslations("FieldRow");
  const displayName = field.name?.trim() || t("noName");

  return (
    <BaseListRow
      onClick={onClick}
      className={cn(
        "cursor-pointer rounded-lg border border-border/60 py-3.5 min-h-14",
        className
      )}
      style={depth > 0 ? { marginLeft: depth * 20 } : undefined}
    >
      <div className="flex items-center gap-0.5 shrink-0 -mr-1">
        {isDraggable && depth === 0 && (
          <div
            {...dragHandleProps}
            className="shrink-0 cursor-grab active:cursor-grabbing text-muted-foreground/50 hover:text-muted-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <GripVertical className="h-4 w-4" />
          </div>
        )}
        {expandable && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand?.();
            }}
            className="rounded-md p-2 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
            aria-label={expanded ? t("collapse") : t("expand")}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {isArrayItem ? (
        <span className="flex-1 min-w-0">
          <span className="inline-flex items-center rounded-md bg-muted/60 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            items
          </span>
        </span>
      ) : (
        <span className="flex-1 min-w-0 font-mono text-xs truncate">
          {displayName}
        </span>
      )}

      <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
        <Select
          value={field.type}
          onValueChange={(value) =>
            value && onTypeChange?.(value as FieldType)
          }
        >
          <SelectTrigger size="sm" className="w-28 text-xs cursor-pointer">
            {(() => {
              const meta = FIELD_TYPE_META[field.type];
              if (!meta) return null;
              const Icon = meta.icon;
              return (
                <span className="flex items-center gap-1.5">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  {meta.label}
                </span>
              );
            })()}
          </SelectTrigger>
          <SelectContent>
            {Object.entries(FIELD_TYPE_META).map(([value, meta]) => {
              const Icon = meta.icon;
              return (
                <SelectItem key={value} value={value}>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  {meta.label}
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      </div>

      <div
        className="shrink-0 flex items-center gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <Switch
          checked={field.enabled ?? true}
          onCheckedChange={onToggleEnabled}
        />
        {onDelete && (
          <button
            type="button"
            aria-label={t("deleteAria")}
            onClick={onDelete}
            className="rounded-md p-2 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </BaseListRow>
  );
}
