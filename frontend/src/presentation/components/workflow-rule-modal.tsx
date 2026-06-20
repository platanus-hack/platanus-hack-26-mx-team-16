"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useWorkflowRuleKindsStore } from "@/src/application/stores/use-workflow-rule-kinds-store";
import { getWorkflowRuleKindUI } from "@/src/application/lib/workflow-rule-kinds";
import { registerDefaultWorkflowRuleKindUIs } from "@/src/application/lib/workflow-rule-kinds-bootstrap";

registerDefaultWorkflowRuleKindUIs();
import type {
  CreateWorkflowRulePayload,
  UpdateWorkflowRulePayload,
  WorkflowRule,
  WorkflowRuleScope,
} from "@/src/domain/entities/workflow-rule";
import type { WorkflowRuleCompilation } from "@/src/domain/entities/workflow-rule-compilation";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpWorkflowRuleRepository } from "@/src/infrastructure/repositories/http-workflow-rule";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";
import { JsonSchemaDrivenForm } from "@/src/presentation/components/json-schema-driven-form";
import {
  type DoctypeRef,
  PromptEditor,
} from "@/src/presentation/components/prompt-editor";
import { WorkflowRuleCompilationSection } from "@/src/presentation/components/workflow-rule-compilation-section";

const ruleRepository = new HttpWorkflowRuleRepository(authHttp);

const DEFAULT_SCOPE: WorkflowRuleScope = {
  mode: "ALL_DOCUMENTS",
  onEmpty: "SKIPPED",
};

interface WorkflowRuleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialRule?: WorkflowRule | null;
  onSubmit: (
    payload: CreateWorkflowRulePayload | UpdateWorkflowRulePayload,
    isUpdate: boolean,
  ) => Promise<void>;
  doctypes?: DoctypeRef[];
  systemVariables?: string[];
  isCompiling?: boolean;
}

export function WorkflowRuleModal({
  open,
  onOpenChange,
  initialRule,
  onSubmit,
  doctypes,
  systemVariables,
  isCompiling = false,
}: WorkflowRuleModalProps) {
  const { kinds, byName, hydrate, hasHydrated, isLoading } =
    useWorkflowRuleKindsStore();

  const isUpdate = Boolean(initialRule);

  const [name, setName] = useState("");
  const [kind, setKind] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [scope, setScope] = useState<WorkflowRuleScope>(DEFAULT_SCOPE);
  const [isActive, setIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [compilation, setCompilation] = useState<WorkflowRuleCompilation | null>(null);
  const [recompiling, setRecompiling] = useState(false);

  const editingRuleId = initialRule?.uuid ?? null;

  useEffect(() => {
    if (open && !hasHydrated) hydrate();
  }, [open, hasHydrated, hydrate]);

  // Fetch latest compilation when modal opens with an editable rule, and
  // re-fetch whenever the SSE-driven `isCompiling` flag flips back to false
  // (i.e. compilation just finished).
  useEffect(() => {
    if (!open || !editingRuleId) {
      setCompilation(null);
      return;
    }
    let cancelled = false;
    ruleRepository.listCompilations(editingRuleId).then((res) => {
      if (cancelled) return;
      if (isErrorFeedback(res)) return;
      setCompilation(res.data[0] ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [open, editingRuleId, isCompiling]);

  useEffect(() => {
    if (!open) return;
    if (initialRule) {
      setName(initialRule.name);
      setKind(initialRule.kind);
      setPrompt(initialRule.prompt);
      setConfig(initialRule.config ?? {});
      setScope({ ...DEFAULT_SCOPE, ...(initialRule.scope ?? {}) });
      setIsActive(initialRule.isActive);
      return;
    }
    setName("");
    setKind(kinds[0]?.name ?? "");
    setPrompt("");
    setConfig(kinds[0]?.defaultConfig ?? {});
    setScope(DEFAULT_SCOPE);
    setIsActive(true);
  }, [open, initialRule, kinds]);

  const selectedKind = byName[kind];
  const KindEditor = useMemo(() => getWorkflowRuleKindUI(kind)?.configEditor, [kind]);

  const handleKindChange = (next: string | null) => {
    if (!next) return;
    setKind(next);
    setConfig(byName[next]?.defaultConfig ?? {});
  };

  const handleRecompile = async () => {
    if (!editingRuleId || recompiling || isCompiling) return;
    setRecompiling(true);
    try {
      await ruleRepository.recompile(editingRuleId);
    } finally {
      setRecompiling(false);
    }
  };

  const handleSubmit = async () => {
    if (!name.trim() || !prompt.trim() || !kind) return;
    setSubmitting(true);
    const payload = {
      name: name.trim(),
      kind,
      prompt,
      config,
      scope,
      isActive,
    };
    try {
      await onSubmit(payload, isUpdate);
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-2xl p-6">
        <DialogHeader>
          <DialogTitle>{isUpdate ? "Editar regla" : "Nueva regla"}</DialogTitle>
        </DialogHeader>

        <DialogBody className="-mx-6 px-6 gap-4">
          <div className="grid grid-cols-[2fr_1fr] gap-3">
            <div className="flex flex-col gap-1.5">
              <Label className="text-sm font-medium">Nombre</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej. Validar firma de la factura"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-sm font-medium">Tipo</Label>
              <Select value={kind} onValueChange={handleKindChange} disabled={isLoading}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Selecciona tipo">
                    {(value) => byName[value as string]?.label ?? value}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {kinds.map((k) => (
                    <SelectItem key={k.name} value={k.name}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="text-sm font-medium">Prompt</Label>
            <PromptEditor
              value={prompt}
              onChange={setPrompt}
              doctypes={doctypes}
              systemVariables={systemVariables}
              placeholder="Describe el criterio. Usa @doctype.field y {{variable}} para referencias."
              minHeightClassName="min-h-[140px]"
            />
            <p className="text-xs text-muted-foreground">
              Referencias: <code>@slug.field</code> a campos extraídos,{" "}
              <code>{"{{variable}}"}</code> a variables del sistema.
            </p>
          </div>

          {selectedKind ? (
            KindEditor ? (
              <section className="flex flex-col overflow-hidden rounded-lg border">
                <header className="border-b bg-muted/30 px-3 py-2">
                  <h4 className="text-sm font-semibold">{selectedKind.label} — config</h4>
                </header>
                <KindEditor rule={initialRule ?? {}} config={config} onChange={setConfig} />
              </section>
            ) : (
              <section className="rounded-lg border p-3">
                <h4 className="mb-2 text-sm font-semibold">{selectedKind.label} — config</h4>
                <JsonSchemaDrivenForm
                  schema={selectedKind.configSchema}
                  value={config}
                  onChange={setConfig}
                />
              </section>
            )
          ) : null}

          <ScopeEditor scope={scope} onChange={setScope} />

          <div className="flex items-center gap-2">
            <Switch id="is-active" checked={isActive} onCheckedChange={setIsActive} />
            <Label htmlFor="is-active">Regla activa</Label>
          </div>

          {isUpdate ? (
            <WorkflowRuleCompilationSection
              compilation={compilation}
              isCompiling={isCompiling || recompiling}
            />
          ) : null}
        </DialogBody>

        <DialogFooter className="sm:justify-between">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <div className="flex items-center gap-2">
            {isUpdate ? (
              <Button
                variant="outline"
                onClick={handleRecompile}
                disabled={recompiling || isCompiling}
              >
                <RefreshCw
                  className={
                    recompiling || isCompiling ? "animate-spin" : undefined
                  }
                />
                {isCompiling
                  ? "Interpretando…"
                  : recompiling
                    ? "Encolando…"
                    : "Reinterpretar"}
              </Button>
            ) : null}
            <Button
              onClick={handleSubmit}
              disabled={submitting || !name.trim() || !prompt.trim() || !kind}
            >
              {submitting ? "Guardando…" : isUpdate ? "Guardar" : "Crear"}
            </Button>
          </div>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

const SCOPE_LABELS: Record<WorkflowRuleScope["mode"], string> = {
  ALL_DOCUMENTS: "Todos los documentos",
  SINGLE_DOCUMENT: "Por cada documento",
  AGGREGATE_OVER_TYPE: "Conjunto por tipo",
  TUPLE_CARTESIAN: "Combinaciones entre tipos",
};

const ON_EMPTY_LABELS: Record<WorkflowRuleScope["onEmpty"], string> = {
  SKIPPED: "Saltar, no afecta al resultado",
  FAILED: "Marcar como fallida",
  PASSED: "Marcar como pasada",
};

function ScopeEditor({
  scope,
  onChange,
}: {
  scope: WorkflowRuleScope;
  onChange: (next: WorkflowRuleScope) => void;
}) {
  return (
    <section className="rounded-lg border p-3">
      <h4 className="mb-2 text-sm font-semibold">Alcance</h4>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label className="text-sm">Modo</Label>
          <Select
            value={scope.mode}
            onValueChange={(next) => {
              if (!next) return;
              onChange({ ...scope, mode: next as WorkflowRuleScope["mode"] });
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue>
                {(value) =>
                  SCOPE_LABELS[value as WorkflowRuleScope["mode"]] ?? value
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {Object.entries(SCOPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label className="text-sm">Si está vacío</Label>
          <Select
            value={scope.onEmpty}
            onValueChange={(next) => {
              if (!next) return;
              onChange({ ...scope, onEmpty: next as WorkflowRuleScope["onEmpty"] });
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue>
                {(value) =>
                  ON_EMPTY_LABELS[value as WorkflowRuleScope["onEmpty"]] ??
                  value
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ON_EMPTY_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </section>
  );
}
