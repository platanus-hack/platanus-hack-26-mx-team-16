"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  type DocumentTypeField,
  FieldType,
} from "@/src/domain/entities/doctype";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import {
  fieldsToJsonSchema,
  jsonSchemaToFields,
  type JsonSchemaNode,
} from "@/src/application/use-cases/json-schema/doctype-schema-converter";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { DocumentTypeFieldRow } from "@/src/presentation/components/doctype-field-row";
import { FieldDetail } from "@/src/presentation/components/field-detail";
import { SortableFieldRow } from "@/src/presentation/components/sortable-field-row";
import { Button } from "@/src/presentation/components/ui/button";

interface OutputSchemaListDetailProps {
  value: JSONSchemaObject;
  onChange: (next: JSONSchemaObject) => void;
}

function generateUuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
}

function isStructured(type: FieldType): boolean {
  return type === FieldType.OBJECT || type === FieldType.ARRAY;
}

function updateFieldByUuid(
  fields: DocumentTypeField[],
  uuid: string,
  updater: (f: DocumentTypeField) => DocumentTypeField
): DocumentTypeField[] {
  return fields.map((f) => {
    if (f.uuid === uuid) return updater(f);
    if (f.children?.length) {
      return { ...f, children: updateFieldByUuid(f.children, uuid, updater) };
    }
    return f;
  });
}

function deleteFieldByUuid(
  fields: DocumentTypeField[],
  uuid: string
): DocumentTypeField[] {
  return fields
    .filter((f) => f.uuid !== uuid)
    .map((f) =>
      f.children?.length
        ? { ...f, children: deleteFieldByUuid(f.children, uuid) }
        : f
    );
}

function addChildToField(
  fields: DocumentTypeField[],
  parentUuid: string,
  child: DocumentTypeField
): DocumentTypeField[] {
  return fields.map((f) => {
    if (f.uuid === parentUuid) {
      const children = [...(f.children ?? []), child].map((c, i) => ({
        ...c,
        order: i,
      }));
      return { ...f, children };
    }
    if (f.children?.length) {
      return { ...f, children: addChildToField(f.children, parentUuid, child) };
    }
    return f;
  });
}

function findFieldByUuid(
  fields: DocumentTypeField[],
  uuid: string,
  parentType?: FieldType
): { field: DocumentTypeField | null; isArrayItem: boolean } {
  for (const f of fields) {
    if (f.uuid === uuid) {
      return { field: f, isArrayItem: parentType === FieldType.ARRAY };
    }
    if (f.children?.length) {
      const r = findFieldByUuid(f.children, uuid, f.type);
      if (r.field) return r;
    }
  }
  return { field: null, isArrayItem: false };
}

interface RowsProps {
  fields: DocumentTypeField[];
  depth: number;
  parentType?: FieldType;
  expandedIds: Set<string>;
  onToggleExpand: (uuid: string) => void;
  onSelect: (uuid: string) => void;
  onToggleEnabled: (uuid: string, enabled: boolean) => void;
  onTypeChange: (uuid: string, type: FieldType) => void;
  onDelete: (uuid: string) => void;
  onAddChild: (parentUuid: string) => void;
  sortable: boolean;
}

function Rows({
  fields,
  depth,
  parentType,
  expandedIds,
  onToggleExpand,
  onSelect,
  onToggleEnabled,
  onTypeChange,
  onDelete,
  onAddChild,
  sortable,
}: RowsProps) {
  const t = useTranslations("OutputSchemaList");
  const isArrayItem = parentType === FieldType.ARRAY;
  return (
    <>
      {fields.map((field) => {
        const expandable = isStructured(field.type);
        const expanded = expandable && expandedIds.has(field.uuid);
        const rowMarkup = (
          dragHandleProps?: React.HTMLAttributes<HTMLDivElement>
        ) => (
          <DocumentTypeFieldRow
            field={field}
            depth={depth}
            expandable={expandable}
            expanded={expanded}
            isArrayItem={isArrayItem}
            onToggleExpand={() => onToggleExpand(field.uuid)}
            onClick={() => onSelect(field.uuid)}
            onToggleEnabled={(v) => onToggleEnabled(field.uuid, v)}
            onTypeChange={(t) => onTypeChange(field.uuid, t)}
            onDelete={isArrayItem ? undefined : () => onDelete(field.uuid)}
            isDraggable={sortable && depth === 0}
            dragHandleProps={dragHandleProps}
          />
        );
        return (
          <Fragment key={field.uuid}>
            {sortable && depth === 0 ? (
              <SortableFieldRow id={field.uuid}>
                {({ setNodeRef, style, attributes, listeners }) => (
                  <div ref={setNodeRef} style={style} {...attributes}>
                    {rowMarkup(
                      listeners as React.HTMLAttributes<HTMLDivElement>
                    )}
                  </div>
                )}
              </SortableFieldRow>
            ) : (
              rowMarkup()
            )}
            {expandable && expanded && (
              <>
                <Rows
                  fields={field.children ?? []}
                  depth={depth + 1}
                  parentType={field.type}
                  expandedIds={expandedIds}
                  onToggleExpand={onToggleExpand}
                  onSelect={onSelect}
                  onToggleEnabled={onToggleEnabled}
                  onTypeChange={onTypeChange}
                  onDelete={onDelete}
                  onAddChild={onAddChild}
                  sortable={false}
                />
                {field.type === FieldType.OBJECT && (
                  <div
                    className="flex items-center py-1"
                    style={{ marginLeft: (depth + 1) * 20 + 4 }}
                  >
                    <button
                      type="button"
                      onClick={() => onAddChild(field.uuid)}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
                    >
                      <Plus className="h-3 w-3" />
                      {t("addProperty")}
                    </button>
                  </div>
                )}
              </>
            )}
          </Fragment>
        );
      })}
    </>
  );
}

export function OutputSchemaListDetail({
  value,
  onChange,
}: OutputSchemaListDetailProps) {
  const t = useTranslations("OutputSchemaList");
  const [fields, setFieldsState] = useState<DocumentTypeField[]>(() =>
    jsonSchemaToFields(value as unknown as JsonSchemaNode)
  );
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [deleteUuid, setDeleteUuid] = useState<string | null>(null);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Re-sync if external value changes (e.g., parent reset / external update)
  const lastSerializedRef = useRef<string>(JSON.stringify(value));
  useEffect(() => {
    const sig = JSON.stringify(value);
    if (sig === lastSerializedRef.current) return;
    lastSerializedRef.current = sig;
    setFieldsState(jsonSchemaToFields(value as unknown as JsonSchemaNode));
  }, [value]);

  const commit = useCallback(
    (next: DocumentTypeField[]) => {
      setFieldsState(next);
      const schema = fieldsToJsonSchema(next) as unknown as JSONSchemaObject;
      lastSerializedRef.current = JSON.stringify(schema);
      onChange(schema);
    },
    [onChange]
  );

  const selected = useMemo(() => {
    if (!selectedUuid)
      return { field: null as DocumentTypeField | null, isArrayItem: false };
    return findFieldByUuid(fields, selectedUuid);
  }, [fields, selectedUuid]);

  const toggleExpand = (uuid: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(uuid)) next.delete(uuid);
      else next.add(uuid);
      return next;
    });
  };

  const handleAddField = () => {
    const newField: DocumentTypeField = {
      uuid: generateUuid(),
      name: "",
      type: FieldType.TEXT,
      required: false,
      enabled: true,
      order: fields.length,
    };
    commit([...fields, newField]);
    setSelectedUuid(newField.uuid);
  };

  const handleToggleEnabled = (uuid: string, enabled: boolean) => {
    commit(updateFieldByUuid(fields, uuid, (f) => ({ ...f, enabled })));
  };

  const handleTypeChange = (uuid: string, type: FieldType) => {
    commit(
      updateFieldByUuid(fields, uuid, (f) => {
        if (type === FieldType.OBJECT) {
          return { ...f, type, children: f.children ?? [] };
        }
        if (type === FieldType.ARRAY) {
          const children =
            f.children && f.children.length > 0
              ? f.children
              : [
                  {
                    uuid: generateUuid(),
                    name: "item",
                    type: FieldType.TEXT,
                    required: false,
                    enabled: true,
                    order: 0,
                  } satisfies DocumentTypeField,
                ];
          return { ...f, type, children };
        }
        return { ...f, type, children: undefined };
      })
    );
  };

  const handleAddChild = (parentUuid: string) => {
    const child: DocumentTypeField = {
      uuid: generateUuid(),
      name: "",
      type: FieldType.TEXT,
      required: false,
      enabled: true,
      order: 0,
    };
    commit(addChildToField(fields, parentUuid, child));
    setExpandedIds((prev) => new Set(prev).add(parentUuid));
    setSelectedUuid(child.uuid);
  };

  const handleConfirmDelete = () => {
    if (!deleteUuid) return;
    commit(deleteFieldByUuid(fields, deleteUuid));
    setDeleteUuid(null);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragId(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIdx = fields.findIndex((f) => f.uuid === active.id);
    const newIdx = fields.findIndex((f) => f.uuid === over.id);
    if (oldIdx < 0 || newIdx < 0) return;
    const reordered = arrayMove(fields, oldIdx, newIdx).map((f, i) => ({
      ...f,
      order: i,
    }));
    commit(reordered);
  };

  const activeField =
    activeDragId !== null
      ? fields.find((f) => f.uuid === activeDragId) ?? null
      : null;

  if (selected.field) {
    const current = selected.field;
    return (
      <FieldDetail
        field={current}
        onBack={() => setSelectedUuid(null)}
        onUpdate={(updated) =>
          commit(updateFieldByUuid(fields, current.uuid, () => updated))
        }
        hideName={selected.isArrayItem}
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {fields.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-sm text-muted-foreground">
          {t("noProperties")}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={() => setActiveDragId(null)}
          >
            <SortableContext
              items={fields.map((f) => f.uuid)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                <Rows
                  fields={fields}
                  depth={0}
                  expandedIds={expandedIds}
                  onToggleExpand={toggleExpand}
                  onSelect={setSelectedUuid}
                  onToggleEnabled={handleToggleEnabled}
                  onTypeChange={handleTypeChange}
                  onDelete={setDeleteUuid}
                  onAddChild={handleAddChild}
                  sortable
                />
              </div>
            </SortableContext>
            <DragOverlay>
              {activeField ? (
                <div className="cursor-grabbing shadow-xl ring-1 ring-primary/30 rounded-lg bg-background">
                  <DocumentTypeFieldRow
                    field={activeField}
                    depth={0}
                    expandable={isStructured(activeField.type)}
                    expanded={false}
                    isArrayItem={false}
                    isDraggable
                  />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        </div>
      )}

      <div className="border-t border-border/50 p-3">
        <Button onClick={handleAddField} className="w-full gap-2">
          <Plus className="h-4 w-4" />
          {t("addPropertyButton")}
        </Button>
      </div>

      <ConfirmDeleteDialog
        open={deleteUuid !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteUuid(null);
        }}
        onConfirm={handleConfirmDelete}
        title={t("deleteTitle")}
        description={t("deleteDescription")}
      />
    </div>
  );
}
