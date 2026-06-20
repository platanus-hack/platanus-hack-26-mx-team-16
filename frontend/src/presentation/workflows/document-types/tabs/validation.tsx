"use client";

import {
  AlertCircle,
  CheckCircle2,
  Plus,
  Sparkles,
  Target,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { flattenSchemaPaths } from "src/application/use-cases/json-schema/flatten-paths";
import type {
  DocumentType,
  ValidationRule as ValidationRuleEntity,
} from "src/domain/entities/doctype";
import type { ValidationRulePayload } from "src/domain/repositories/doctype";
import { ConfirmDeleteDialog } from "src/presentation/components/common/confirm-delete-dialog";
import { HighlightPrompt } from "src/presentation/components/prompt-highlight";
import { Button } from "src/presentation/components/ui/button";
import { ValidationRule } from "src/presentation/components/validation-rule";
import { ValidationRuleDetail } from "src/presentation/components/validation-rule-detail";
import { EmptyState } from "@/src/presentation/components/common/empty-state";

interface ValidationTabProps {
  doctype: DocumentType;
  onUpdate: () => void;
  onPersistRules?: (rules: ValidationRulePayload[]) => Promise<void>;
}

interface RuleDraft {
  id: string;
  name: string;
  prompt: string;
  enabled: boolean;
  missingHandling: "skip" | "fail" | "pass" | "ignore";
}

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID)
    return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function draftToPayload(rules: RuleDraft[]): ValidationRulePayload[] {
  return rules.map((r) => ({
    id: r.id,
    name: r.name,
    prompt: r.prompt,
    enabled: r.enabled,
    missingHandling: r.missingHandling,
  }));
}

function draftToEntity(
  draft: RuleDraft,
  untitledLabel: string
): ValidationRuleEntity {
  return {
    uuid: draft.id,
    name: draft.name || untitledLabel,
    enabled: draft.enabled,
    type: "document",
    prompt: draft.prompt,
    missingDataHandling: draft.missingHandling,
  };
}

function entityToDraft(
  entity: ValidationRuleEntity,
  fallback: RuleDraft
): RuleDraft {
  return {
    ...fallback,
    id: fallback.id,
    name: entity.name ?? fallback.name,
    prompt: entity.prompt ?? fallback.prompt,
    enabled: entity.enabled,
    missingHandling:
      (entity.missingDataHandling as RuleDraft["missingHandling"]) ??
      fallback.missingHandling,
  };
}

function deriveName(prompt: string, id: string): string {
  const trimmed = prompt.trim();
  if (!trimmed) return id;
  const first = trimmed.split(/[.!?\n]/)[0];
  return first.length > 60 ? `${first.slice(0, 57)}…` : first;
}

export function DocumentTypeValidationTab({
  doctype,
  onPersistRules,
}: ValidationTabProps) {
  const t = useTranslations("DoctypeValidationTab");
  const initial = useMemo<RuleDraft[]>(() => {
    const raw = (doctype.validationRules ?? []) as unknown as Array<
      Partial<RuleDraft> & { uuid?: string; missing_handling?: string }
    >;
    return raw.map((r, i) => ({
      id: r.id || r.uuid || `v-${i + 1}`,
      name: r.name || "",
      prompt: r.prompt ?? "",
      enabled: r.enabled ?? true,
      missingHandling:
        (r.missingHandling as RuleDraft["missingHandling"]) ||
        (r.missing_handling as RuleDraft["missingHandling"]) ||
        "fail",
    }));
  }, [doctype.validationRules]);

  const fieldPaths = useMemo(
    () => flattenSchemaPaths(doctype.fields),
    [doctype.fields]
  );

  const router = useRouter();
  const searchParams = useSearchParams();
  const ruleParam = searchParams.get("rule");

  const [rules, setRules] = useState<RuleDraft[]>(initial);
  const selectedIdx = useMemo(() => {
    if (!ruleParam) return null;
    const idx = rules.findIndex((r) => r.id === ruleParam);
    return idx === -1 ? null : idx;
  }, [rules, ruleParam]);
  const openRule = useCallback(
    (id: string) => {
      const next = new URLSearchParams(searchParams.toString());
      next.set("rule", id);
      router.push(`?${next.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );
  const closeRuleDetail = useCallback(() => {
    router.back();
  }, [router]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedToast, setSavedToast] = useState(false);
  const [deleteIdx, setDeleteIdx] = useState<number | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setRules((prev) => {
      if (prev.length === 0) return initial;
      const initialById = new Map(initial.map((r) => [r.id, r]));
      const seenIds = new Set<string>();
      const merged: RuleDraft[] = [];
      for (const r of prev) {
        const updated = initialById.get(r.id);
        if (updated) {
          merged.push(updated);
          seenIds.add(r.id);
        }
      }
      for (const r of initial) {
        if (!seenIds.has(r.id)) merged.push(r);
      }
      return merged;
    });
  }, [initial]);

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  const flashSavedToast = useCallback(() => {
    setSavedToast(true);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setSavedToast(false), 2200);
  }, []);

  const persist = useCallback(
    async (next: RuleDraft[]): Promise<boolean> => {
      if (!onPersistRules) return false;
      setIsSaving(true);
      setError(null);
      try {
        await onPersistRules(
          draftToPayload(
            next.map((r) => ({
              ...r,
              name: r.name || deriveName(r.prompt, r.id),
            }))
          )
        );
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : t("saveError"));
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [onPersistRules, t]
  );

  const debouncedPersist = useCallback(
    (next: RuleDraft[]) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => persist(next), 600);
    },
    [persist]
  );

  const addRule = useCallback(() => {
    const newDraft: RuleDraft = {
      id: generateId(),
      name: "",
      prompt: "",
      enabled: true,
      missingHandling: "fail",
    };
    const next = [...rules, newDraft];
    setRules(next);
    openRule(newDraft.id);
  }, [openRule, rules]);

  const toggleRule = useCallback(
    (idx: number, enabled: boolean) => {
      const next = rules.map((r, i) => (i === idx ? { ...r, enabled } : r));
      setRules(next);
      void persist(next);
    },
    [persist, rules]
  );

  const deleteRuleAt = useCallback(
    (idx: number) => {
      const next = rules.filter((_, i) => i !== idx);
      setRules(next);
      void persist(next);
    },
    [persist, rules]
  );

  const updateSelected = useCallback(
    (patch: ValidationRuleEntity) => {
      if (selectedIdx === null) return;
      const current = rules[selectedIdx];
      const merged = entityToDraft(patch, current);
      const next = rules.map((r, i) => (i === selectedIdx ? merged : r));
      setRules(next);
      debouncedPersist(next);
    },
    [debouncedPersist, rules, selectedIdx]
  );

  const backToList = useCallback(() => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
      persist(rules);
    }
    closeRuleDetail();
  }, [closeRuleDetail, persist, rules]);

  const saveSelected = useCallback(async () => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
    const ok = await persist(rules);
    if (ok) flashSavedToast();
  }, [flashSavedToast, persist, rules]);

  if (selectedIdx !== null && rules[selectedIdx]) {
    return (
      <div className="relative h-full">
        <ValidationRuleDetail
          key={rules[selectedIdx].id}
          rule={draftToEntity(rules[selectedIdx], t("untitledRule"))}
          onBack={backToList}
          onUpdate={updateSelected}
          onSave={saveSelected}
          fieldPaths={fieldPaths}
        />
        <SavedToast visible={savedToast} message={t("savedToast")} />
        {error && (
          <div
            role="alert"
            className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 backdrop-blur px-3 py-2 text-xs text-destructive shadow-md"
          >
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  if (rules.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <EmptyState
          icon={Target}
          title={t("emptyTitle")}
          description={t("emptyDescription")}
          actionLabel={t("addValidationRule")}
          onAction={addRule}
        />
        {error && (
          <div
            role="alert"
            className="mx-4 mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
          >
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {rules.map((rule, idx) => {
            const title =
              rule.name.trim() ||
              deriveName(rule.prompt, rule.id) ||
              t("noName");
            return (
              <ValidationRule
                key={rule.id}
                rule={{
                  uuid: rule.id,
                  name: title,
                  enabled: rule.enabled,
                  type: "document",
                  prompt: rule.prompt,
                }}
                label={
                  <div className="flex flex-col gap-1.5 min-w-0">
                    <div className="text-sm font-medium truncate">{title}</div>
                    <div className="text-xs text-muted-foreground line-clamp-2">
                      {rule.prompt.trim() ? (
                        <HighlightPrompt
                          text={rule.prompt}
                          paths={fieldPaths}
                        />
                      ) : (
                        <span className="italic">{t("noPrompt")}</span>
                      )}
                    </div>
                  </div>
                }
                className="rounded-lg border border-border/60 border-b min-h-16"
                onClick={() => openRule(rule.id)}
                onToggle={(v) => toggleRule(idx, v)}
                onDelete={() => setDeleteIdx(idx)}
              />
            );
          })}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="mx-4 mb-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="border-t border-border/50 p-3 flex items-center gap-2">
        <Button onClick={addRule} className="gap-2 flex-1">
          <Plus className="h-4 w-4" />
          {t("addRule")}
        </Button>
        <Button variant="outline" onClick={() => {}} className="gap-2 flex-1">
          <Sparkles className="h-4 w-4" />
          {t("suggestRules")}
        </Button>
        {isSaving && (
          <span className="text-xs text-muted-foreground shrink-0">
            {t("saving")}
          </span>
        )}
      </div>
      <SavedToast visible={savedToast} message={t("savedToast")} />

      <ConfirmDeleteDialog
        open={deleteIdx !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteIdx(null);
        }}
        onConfirm={() => {
          if (deleteIdx !== null) deleteRuleAt(deleteIdx);
          setDeleteIdx(null);
        }}
        title={t("deleteTitle")}
        description={t("deleteDescription")}
      />
    </div>
  );
}

function SavedToast({
  visible,
  message,
}: {
  visible: boolean;
  message: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 backdrop-blur px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 shadow-md transition-all duration-200 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
      }`}
    >
      <CheckCircle2 className="h-3.5 w-3.5" />
      {message}
    </div>
  );
}
