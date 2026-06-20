"use client";

import { AlertCircle, AlignLeft, FileJson, Plus, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
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
import type {
  DocumentType,
  DocumentTypeField,
  FieldType,
} from "src/domain/entities/doctype";
import { FieldType as FieldTypeEnum } from "src/domain/entities/doctype";
import { DocumentTypeFieldRow } from "src/presentation/components/doctype-field-row";
import { SortableFieldRow } from "src/presentation/components/sortable-field-row";
import { Button } from "src/presentation/components/ui/button";
import { ConfirmDeleteDialog } from "src/presentation/components/common/confirm-delete-dialog";
import {
  jsonSchemaToFields,
  type JsonSchemaNode,
} from "src/application/use-cases/json-schema/doctype-schema-converter";
import { useSuggestFieldsMutation } from "src/application/hooks/queries/document-types";
import { useBackgroundTasksStore } from "src/application/stores/background-tasks-store";
import { SuggestFieldsModal } from "../detail/suggest-fields-modal";

interface FieldsTabProps {
  doctype: DocumentType;
  fields: DocumentTypeField[];
  onFieldsChange: (fields: DocumentTypeField[]) => void;
  onUpdate: () => void;
  onSelectField: (field: DocumentTypeField, isArrayItem?: boolean) => void;
  onPersistImport?: () => Promise<void>;
  onSuggestFieldsStarted?: () => void;
  expandedIds: Set<string>;
  onExpandedIdsChange: (next: Set<string>) => void;
}

function generateUuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
}

function isStructured(type: FieldType): boolean {
  return type === FieldTypeEnum.OBJECT || type === FieldTypeEnum.ARRAY;
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

interface FieldRowsProps {
  fields: DocumentTypeField[];
  depth: number;
  expandedIds: Set<string>;
  onToggleExpand: (uuid: string) => void;
  onSelectField: (field: DocumentTypeField, isArrayItem?: boolean) => void;
  onToggleEnabled: (uuid: string, enabled: boolean) => void;
  onTypeChange: (uuid: string, type: FieldType) => void;
  onDelete: (uuid: string) => void;
  onAddChild: (parentUuid: string) => void;
  parentType?: FieldType;
  sortable: boolean;
}

function FieldRows({
  fields,
  depth,
  expandedIds,
  onToggleExpand,
  onSelectField,
  onToggleEnabled,
  onTypeChange,
  onDelete,
  onAddChild,
  parentType,
  sortable,
}: FieldRowsProps) {
  const t = useTranslations("DoctypeFieldsTab");
  const isArrayItem = parentType === FieldTypeEnum.ARRAY;
  return (
    <>
      {fields.map((field) => {
        const expandable = isStructured(field.type);
        const expanded = expandable && expandedIds.has(field.uuid);
        const isSortable = sortable && depth === 0;
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
            onClick={() => onSelectField(field, isArrayItem)}
            onToggleEnabled={(v) => onToggleEnabled(field.uuid, v)}
            onTypeChange={(t) => onTypeChange(field.uuid, t)}
            onDelete={isArrayItem ? undefined : () => onDelete(field.uuid)}
            isDraggable={isSortable}
            dragHandleProps={dragHandleProps}
          />
        );
        return (
          <Fragment key={field.uuid}>
            {isSortable ? (
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
                <FieldRows
                  fields={field.children ?? []}
                  depth={depth + 1}
                  expandedIds={expandedIds}
                  onToggleExpand={onToggleExpand}
                  onSelectField={onSelectField}
                  onToggleEnabled={onToggleEnabled}
                  onTypeChange={onTypeChange}
                  onDelete={onDelete}
                  onAddChild={onAddChild}
                  parentType={field.type}
                  sortable={false}
                />
                {field.type === FieldTypeEnum.OBJECT && (
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

export function DocumentTypeFieldsTab({
  doctype,
  fields,
  onFieldsChange,
  onUpdate,
  onSelectField,
  onPersistImport,
  onSuggestFieldsStarted,
  expandedIds,
  onExpandedIdsChange,
}: FieldsTabProps) {
  const t = useTranslations("DoctypeFieldsTab");
  const canSuggestFields =
    Boolean(doctype.sampleFileId) && Boolean(doctype.sampleFileText);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );
  const [importError, setImportError] = useState<string | null>(null);
  const [deleteFieldUuid, setDeleteFieldUuid] = useState<string | null>(null);
  const [isSuggestModalOpen, setIsSuggestModalOpen] = useState(false);
  const importInputRef = useRef<HTMLInputElement>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const suggestMutation = useSuggestFieldsMutation();
  const addTask = useBackgroundTasksStore((s) => s.addTask);

  useEffect(() => {
    return () => {
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    };
  }, []);

  const showImportError = useCallback((message: string) => {
    setImportError(message);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => setImportError(null), 5000);
  }, []);

  const toggleExpand = useCallback(
    (uuid: string) => {
      const next = new Set(expandedIds);
      if (next.has(uuid)) next.delete(uuid);
      else next.add(uuid);
      onExpandedIdsChange(next);
    },
    [expandedIds, onExpandedIdsChange]
  );

  const handleSuggestFields = useCallback(
    async (prompt: string) => {
      await suggestMutation.mutateAsync({
        doctypeId: doctype.uuid,
        prompt: prompt || undefined,
      });
      setIsSuggestModalOpen(false);
      onSuggestFieldsStarted?.();
      addTask({
        label: t("generatingFields"),
        entityId: doctype.uuid,
        entityType: "doctype-fields",
        entityLabel: doctype.name,
      });
      onUpdate();
    },
    [
      addTask,
      doctype.uuid,
      doctype.name,
      suggestMutation,
      onSuggestFieldsStarted,
      onUpdate,
    ]
  );

  const handleImportClick = useCallback(() => {
    setImportError(null);
    importInputRef.current?.click();
  }, []);

  const handleImportFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = JSON.parse(text) as JsonSchemaNode;
        if (!parsed || typeof parsed !== "object" || parsed.type !== "object") {
          throw new Error(t("invalidJsonSchema"));
        }
        const imported = jsonSchemaToFields(parsed);
        if (!imported.length) {
          throw new Error(t("schemaNoFields"));
        }
        onFieldsChange(imported);
        if (onPersistImport) {
          try {
            await onPersistImport();
          } catch (err) {
            showImportError(
              err instanceof Error ? err.message : t("backendRejected")
            );
            return;
          }
        }
        onUpdate();
      } catch (err) {
        showImportError(
          err instanceof Error ? err.message : t("importFailed")
        );
      }
    },
    [onPersistImport, onFieldsChange, onUpdate, showImportError]
  );

  const addField = (type: FieldType = "text" as FieldType) => {
    const newField: DocumentTypeField = {
      uuid: generateUuid(),
      name: "",
      type,
      required: false,
      enabled: true,
      order: fields.length,
      children: isStructured(type) ? [] : undefined,
    };
    onFieldsChange([...fields, newField]);
    onSelectField(newField);
  };

  const handleToggleEnabled = (uuid: string, enabled: boolean) => {
    onFieldsChange(updateFieldByUuid(fields, uuid, (f) => ({ ...f, enabled })));
  };

  const handleTypeChange = (uuid: string, type: FieldType) => {
    onFieldsChange(
      updateFieldByUuid(fields, uuid, (f) => {
        if (type === FieldTypeEnum.OBJECT) {
          return { ...f, type, children: f.children ?? [] };
        }
        if (type === FieldTypeEnum.ARRAY) {
          const children =
            f.children && f.children.length > 0
              ? f.children
              : [
                  {
                    uuid: generateUuid(),
                    name: "item",
                    type: FieldTypeEnum.TEXT,
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

  const handleDeleteRequest = (uuid: string) => {
    setDeleteFieldUuid(uuid);
  };

  const handleConfirmDelete = () => {
    if (!deleteFieldUuid) return;
    onFieldsChange(deleteFieldByUuid(fields, deleteFieldUuid));
    setDeleteFieldUuid(null);
  };

  const handleAddChild = (parentUuid: string) => {
    const child: DocumentTypeField = {
      uuid: generateUuid(),
      name: "",
      type: FieldTypeEnum.TEXT,
      required: false,
      enabled: true,
      order: 0,
    };
    onFieldsChange(addChildToField(fields, parentUuid, child));
    onExpandedIdsChange(new Set(expandedIds).add(parentUuid));
    onSelectField(child);
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
    onFieldsChange(reordered);
  };

  const activeDragField =
    activeDragId !== null
      ? fields.find((f) => f.uuid === activeDragId) ?? null
      : null;

  const hiddenImportInput = (
    <input
      ref={importInputRef}
      type="file"
      accept="application/json,.json"
      className="hidden"
      onChange={handleImportFile}
    />
  );

  if (fields.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-full">
        {hiddenImportInput}
        <div className="flex flex-col items-center text-center max-w-md px-4">
          <div className="mb-6 rounded-full bg-muted/50 p-8">
            <AlignLeft className="h-12 w-12 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">{t("emptyTitle")}</h3>
          <p className="text-sm text-muted-foreground mb-6">
            {t("emptyDescription")}
          </p>
          <div className="flex items-center gap-2 w-full">
            <Button onClick={() => addField()} className="gap-2 flex-1">
              <Plus className="h-4 w-4" />
              {t("addField")}
            </Button>
            <Button
              variant="outline"
              onClick={handleImportClick}
              className="gap-2 flex-1"
            >
              <FileJson className="h-4 w-4" />
              {t("importJson")}
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsSuggestModalOpen(true)}
              className="gap-2 flex-1"
              disabled={!canSuggestFields}
            >
              <Sparkles className="h-4 w-4" />
              {t("suggestFields")}
            </Button>
          </div>
          {importError && (
            <div
              role="alert"
              className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-left text-xs text-destructive"
            >
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>{importError}</span>
            </div>
          )}
        </div>
        <SuggestFieldsModal
          open={isSuggestModalOpen}
          onOpenChange={setIsSuggestModalOpen}
          onSuggest={handleSuggestFields}
          hasExistingFields={Boolean(
            doctype.fields && Object.keys(doctype.fields).length > 0
          )}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {hiddenImportInput}
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
              <FieldRows
                fields={fields}
                depth={0}
                expandedIds={expandedIds}
                onToggleExpand={toggleExpand}
                onSelectField={onSelectField}
                onToggleEnabled={handleToggleEnabled}
                onTypeChange={handleTypeChange}
                onDelete={handleDeleteRequest}
                onAddChild={handleAddChild}
                sortable
              />
            </div>
          </SortableContext>
          <DragOverlay>
            {activeDragField ? (
              <div className="cursor-grabbing shadow-xl ring-1 ring-primary/30 rounded-lg bg-background">
                <DocumentTypeFieldRow
                  field={activeDragField}
                  depth={0}
                  expandable={isStructured(activeDragField.type)}
                  expanded={false}
                  isArrayItem={false}
                  isDraggable
                />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {importError && (
        <div
          role="alert"
          className="mx-4 mb-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{importError}</span>
        </div>
      )}

      <ConfirmDeleteDialog
        open={deleteFieldUuid !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteFieldUuid(null);
        }}
        onConfirm={handleConfirmDelete}
        title={t("deleteTitle")}
        description={t("deleteDescription")}
      />

      <div className="border-t border-border/50 p-3 flex items-center gap-2">
        <Button onClick={() => addField()} className="gap-2 flex-1">
          <Plus className="h-4 w-4" />
          {t("addField")}
        </Button>
        <Button
          variant="outline"
          onClick={handleImportClick}
          className="gap-2 flex-1"
        >
          <FileJson className="h-4 w-4" />
          {t("importJson")}
        </Button>
        <Button
          variant="outline"
          onClick={() => setIsSuggestModalOpen(true)}
          className="gap-2 flex-1"
          disabled={!canSuggestFields}
        >
          <Sparkles className="h-4 w-4" />
          {t("suggestFields")}
        </Button>
      </div>

      <SuggestFieldsModal
        open={isSuggestModalOpen}
        onOpenChange={setIsSuggestModalOpen}
        onSuggest={handleSuggestFields}
      />
    </div>
  );
}
