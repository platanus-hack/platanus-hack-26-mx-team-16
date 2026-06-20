"use client";

import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  type Modifier,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Loader2, Pencil, Scale, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import {
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import {
  type WorkflowRuleEvent,
  useWorkflowRuleEvents,
} from "@/src/application/hooks/use-workflow-rule-events";
import { useWorkflowRuleKindsStore } from "@/src/application/stores/use-workflow-rule-kinds-store";
import type {
  CreateWorkflowRulePayload,
  UpdateWorkflowRulePayload,
  WorkflowRule,
} from "@/src/domain/entities/workflow-rule";
import { flattenSchemaPaths } from "@/src/application/use-cases/json-schema/flatten-paths";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpDocumentTypeRepository } from "@/src/infrastructure/repositories/http-doctype";
import { HttpWorkflowRuleImportExportRepository } from "@/src/infrastructure/repositories/http-workflow-rule-import-export";
import { HttpWorkflowRuleRepository } from "@/src/infrastructure/repositories/http-workflow-rule";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import type { DoctypeRef } from "@/src/presentation/components/prompt-editor";
import { HighlightPrompt } from "@/src/presentation/components/prompt-highlight";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/src/presentation/components/ui/alert-dialog";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";
import { WorkflowRuleImportModal } from "@/src/presentation/components/workflow-rule-import-modal";
import { WorkflowRuleModal } from "@/src/presentation/components/workflow-rule-modal";

const restrictToVerticalAxis: Modifier = ({ transform }) => ({ ...transform, x: 0 });
const ruleRepository = new HttpWorkflowRuleRepository(authHttp);
const doctypeRepository = new HttpDocumentTypeRepository(authHttp);
const importExportRepository = new HttpWorkflowRuleImportExportRepository(authHttp);

const SYSTEM_VARIABLES = ["fecha-hoy", "datetime-now"];

function toHandle(slug: string | null | undefined, fallbackName: string): string {
  const source = (slug && slug.trim()) || fallbackName;
  return (
    source
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/(^_|_$)/g, "") || "doctype"
  );
}

interface AnalysisRulesContentProps {
  workflowId: string;
  onCreateRef?: RefObject<(() => void) | null>;
  onImportRef?: RefObject<(() => void) | null>;
  onExportRef?: RefObject<(() => void) | null>;
}

export function AnalysisRulesContent({
  workflowId,
  onCreateRef,
  onImportRef,
  onExportRef,
}: AnalysisRulesContentProps) {
  const t = useTranslations("AnalysisRulesContent");
  const [rules, setRules] = useState<WorkflowRule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<WorkflowRule | null>(null);
  const [ruleToDelete, setRuleToDelete] = useState<WorkflowRule | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [compilingIds, setCompilingIds] = useState<ReadonlySet<string>>(() => new Set());
  const [doctypeRefs, setDoctypeRefs] = useState<DoctypeRef[]>([]);
  const [, startEventTransition] = useTransition();

  const { hydrate, hasHydrated, byName } = useWorkflowRuleKindsStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  useEffect(() => {
    if (!hasHydrated) hydrate();
  }, [hasHydrated, hydrate]);

  useEffect(() => {
    let cancelled = false;
    doctypeRepository.getAll(workflowId).then((res) => {
      if (cancelled || !("data" in res)) return;
      const refs: DoctypeRef[] = res.data.map((dt) => ({
        name: toHandle(dt.slug, dt.name),
        paths: flattenSchemaPaths(dt.fields),
      }));
      setDoctypeRefs(refs);
    });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const loadRules = useCallback(async () => {
    setIsLoading(true);
    const response = await ruleRepository.list(workflowId);
    if ("data" in response) setRules(response.data);
    setIsLoading(false);
  }, [workflowId]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  useEffect(() => {
    let cancelled = false;
    ruleRepository.getCompilingState(workflowId).then((res) => {
      if (cancelled) return;
      if (!("ruleIds" in res)) return;
      setCompilingIds(new Set(res.ruleIds));
    });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const handleCreate = useCallback(() => {
    setEditingRule(null);
    setModalOpen(true);
  }, []);

  const handleImport = useCallback(() => setImportOpen(true), []);

  const handleExport = useCallback(async () => {
    const envelope = await importExportRepository.export(workflowId);
    if (isErrorFeedback(envelope)) return;
    const blob = new Blob([JSON.stringify(envelope, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `workflow-rules-${workflowId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [workflowId]);

  useEffect(() => {
    if (onCreateRef) onCreateRef.current = handleCreate;
    if (onImportRef) onImportRef.current = handleImport;
    if (onExportRef) onExportRef.current = handleExport;
  });

  const handleEvent = useCallback(
    (event: WorkflowRuleEvent) => {
      startEventTransition(() => {
        if (event.type === "COMPILATION_STARTED") {
          setCompilingIds((prev) => {
            const next = new Set(prev);
            next.add(event.ruleId);
            return next;
          });
          return;
        }
        if (
          event.type === "COMPILATION_COMPLETED" ||
          event.type === "COMPILATION_FAILED" ||
          event.type === "COMPILATION_INVALIDATED"
        ) {
          setCompilingIds((prev) => {
            const next = new Set(prev);
            next.delete(event.ruleId);
            return next;
          });
          loadRules();
        }
      });
    },
    [loadRules],
  );

  useWorkflowRuleEvents(workflowId, handleEvent);

  const handleSubmit = async (
    payload: CreateWorkflowRulePayload | UpdateWorkflowRulePayload,
    isUpdate: boolean,
  ) => {
    if (isUpdate && editingRule) {
      const response = await ruleRepository.update(editingRule.uuid, payload);
      if ("data" in response) {
        setRules((prev) =>
          prev.map((r) => (r.uuid === editingRule.uuid ? response.data : r)),
        );
      }
      return;
    }
    const response = await ruleRepository.create(workflowId, payload as CreateWorkflowRulePayload);
    if ("data" in response) setRules((prev) => [...prev, response.data]);
  };

  const handleToggle = async (rule: WorkflowRule, isActive: boolean) => {
    const response = await ruleRepository.update(rule.uuid, { isActive });
    if ("data" in response) {
      setRules((prev) => prev.map((r) => (r.uuid === rule.uuid ? response.data : r)));
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = rules.findIndex((r) => r.uuid === active.id);
    const newIndex = rules.findIndex((r) => r.uuid === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const previous = rules;
    const reordered = arrayMove(rules, oldIndex, newIndex);
    setRules(reordered);

    const response = await ruleRepository.reorder(
      workflowId,
      reordered.map((r) => r.uuid),
    );
    if ("data" in response) setRules(response.data);
    else setRules(previous);
  };

  const confirmDelete = async () => {
    if (!ruleToDelete) return;
    const response = await ruleRepository.delete(ruleToDelete.uuid);
    if ("status" in response) {
      setRules((prev) => prev.filter((r) => r.uuid !== ruleToDelete.uuid));
    }
    setRuleToDelete(null);
  };

  if (isLoading) {
    return (
      <div className="flex h-full flex-1 items-center justify-center">
        <div className="text-sm text-muted-foreground">{t("loading")}</div>
      </div>
    );
  }

  if (rules.length === 0) {
    return (
      <>
        <div className="flex h-full flex-1 items-center justify-center">
          <EmptyState
            icon={Scale}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={t("newRule")}
            onAction={handleCreate}
          />
        </div>
        <WorkflowRuleModal
          open={modalOpen}
          onOpenChange={setModalOpen}
          initialRule={null}
          onSubmit={handleSubmit}
          doctypes={doctypeRefs}
          systemVariables={SYSTEM_VARIABLES}
        />
        <WorkflowRuleImportModal
          open={importOpen}
          onOpenChange={setImportOpen}
          workflowId={workflowId}
          onImported={loadRules}
        />
      </>
    );
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={rules.map((r) => r.uuid)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex flex-col gap-3">
            {rules.map((rule) => (
              <SortableWorkflowRuleCard
                key={rule.uuid}
                rule={rule}
                kindLabel={byName[rule.kind]?.label ?? rule.kind}
                isCompiling={compilingIds.has(rule.uuid)}
                onEdit={() => {
                  setEditingRule(rule);
                  setModalOpen(true);
                }}
                onToggle={(next) => handleToggle(rule, next)}
                onDelete={() => setRuleToDelete(rule)}
                doctypes={doctypeRefs}
                systemVariables={SYSTEM_VARIABLES}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <WorkflowRuleModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        initialRule={editingRule}
        onSubmit={handleSubmit}
        doctypes={doctypeRefs}
        systemVariables={SYSTEM_VARIABLES}
        isCompiling={editingRule ? compilingIds.has(editingRule.uuid) : false}
      />

      <WorkflowRuleImportModal
        open={importOpen}
        onOpenChange={setImportOpen}
        workflowId={workflowId}
        onImported={loadRules}
      />

      <AlertDialog
        open={ruleToDelete !== null}
        onOpenChange={(open) => {
          if (!open) setRuleToDelete(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription", {
                name: ruleToDelete?.name || t("noName"),
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={confirmDelete}
            >
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

interface SortableWorkflowRuleCardProps {
  rule: WorkflowRule;
  kindLabel: string;
  isCompiling: boolean;
  onEdit: () => void;
  onToggle: (isActive: boolean) => void;
  onDelete: () => void;
  doctypes?: DoctypeRef[];
  systemVariables?: string[];
}

function VerifiedBadge() {
  const t = useTranslations("AnalysisRulesContent");
  return (
    <svg
      className="h-5 w-5 shrink-0"
      viewBox="0 0 24 24"
      role="img"
      aria-label={t("interpretedAria")}
    >
      <path
        d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"
        className="fill-violet-200 dark:fill-violet-400/40"
      />
      <path
        d="m8.5 12.3 2.4 2.4 4.6-5.2"
        className="stroke-violet-700 dark:stroke-violet-200"
        fill="none"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const stopPropagation = (e: { stopPropagation(): void }) => e.stopPropagation();

function SortableWorkflowRuleCard({
  rule,
  kindLabel,
  isCompiling,
  onEdit,
  onToggle,
  onDelete,
  doctypes,
  systemVariables,
}: SortableWorkflowRuleCardProps) {
  const t = useTranslations("AnalysisRulesContent");
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } =
    useSortable({ id: rule.uuid });
  const style = useMemo(
    () => ({
      transform: CSS.Transform.toString(transform),
      transition,
    }),
    [transform, transition],
  );

  const handleCardClick = () => {
    if (isDragging) return;
    onEdit();
  };

  const handleCardKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onEdit();
    }
  };

  const showVerified = !isCompiling && rule.currentCompilationId !== null;

  return (
    <div
      ref={setNodeRef}
      style={style}
      role="button"
      tabIndex={0}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      className={cn(
        "rounded-xl border bg-background p-5 transition-all outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        isDragging
          ? "z-10 cursor-grabbing border-border shadow-lg shadow-foreground/5 ring-1 ring-border"
          : "cursor-pointer border-border hover:border-foreground/20 hover:bg-muted/40 hover:shadow-sm",
        isCompiling && "border-violet-500/30 bg-violet-500/[0.04]",
      )}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          ref={setActivatorNodeRef}
          aria-label={t("reorderAria")}
          onClick={stopPropagation}
          className={cn(
            "-ml-1 flex h-9 w-5 shrink-0 items-center justify-center rounded-md text-muted-foreground/40 transition-colors hover:text-muted-foreground touch-none select-none",
            isDragging ? "cursor-grabbing text-muted-foreground" : "cursor-grab",
          )}
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>

        <div className="flex-1 min-w-0">
          <div className="mb-2 flex items-center gap-1.5">
            <h4 className="font-semibold text-base truncate">
              {rule.name || t("noName")}
            </h4>
            {showVerified ? <VerifiedBadge /> : null}
            {isCompiling ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-violet-600 dark:bg-violet-500/15 dark:text-violet-300">
                <Loader2 className="h-3 w-3 animate-spin" />
                {t("interpreting")}
              </span>
            ) : null}
            <Badge variant="secondary" className="ml-auto shrink-0">
              {kindLabel}
            </Badge>
          </div>
          <div
            className="max-h-32 overflow-y-auto overscroll-contain rounded-md bg-muted/50 border border-border/30 px-3 py-2"
            onClick={stopPropagation}
            onKeyDown={stopPropagation}
            onWheel={stopPropagation}
          >
            <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
              <HighlightPrompt
                text={rule.prompt}
                doctypes={doctypes}
                systemVariables={systemVariables}
              />
            </p>
          </div>
        </div>

        <div
          className="flex items-center gap-3 shrink-0 pt-1"
          onClick={stopPropagation}
          onKeyDown={stopPropagation}
        >
          <Switch checked={rule.isActive} onCheckedChange={onToggle} />
          <button
            type="button"
            aria-label={t("editAria")}
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="text-muted-foreground/70 hover:text-foreground transition-colors p-1 cursor-pointer"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label={t("deleteAria")}
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="text-destructive/60 hover:text-destructive transition-colors p-1 cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
