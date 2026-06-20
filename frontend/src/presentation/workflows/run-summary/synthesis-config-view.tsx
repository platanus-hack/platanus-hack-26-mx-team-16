"use client";

import { Check } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useState,
} from "react";

import { useWorkflowSynthesisConfigStore } from "@/src/application/stores/workflow-synthesis-config-store";
import { cn } from "@/src/application/lib/utils";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/src/presentation/components/ui/alert";
import { Button } from "@/src/presentation/components/ui/button";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Label } from "@/src/presentation/components/ui/label";
import { MarkdownRichEditor } from "@/src/presentation/components/ui/markdown-rich-editor";
import { Switch } from "@/src/presentation/components/ui/switch";

import { OutputSchemaEditor } from "./output-schema-editor";
import {
  DEFAULT_TOKEN_REGISTRY,
  TokenChipPalette,
} from "./token-chip-palette";

export interface SynthesisConfigViewHandle {
  save: () => Promise<void>;
}

interface SynthesisConfigViewProps {
  workflowId: string;
}

interface FormState {
  outputSchema: JSONSchemaObject | null;
  synthesisTemplate: string;
  synthesisEnabled: boolean;
}

export const SynthesisConfigView = forwardRef<
  SynthesisConfigViewHandle,
  SynthesisConfigViewProps
>(function SynthesisConfigView({ workflowId }, ref) {
  const t = useTranslations("SynthesisConfig");
  const locale = useLocale();
  const {
    configByWorkflow,
    loading,
    saving,
    errors,
    loadConfig,
    updateConfig,
  } = useWorkflowSynthesisConfigStore();

  const isLoading = !!loading[workflowId];
  const isSaving = !!saving[workflowId];
  const error = errors[workflowId] ?? null;
  const initialConfig = configByWorkflow[workflowId] ?? null;

  const [form, setForm] = useState<FormState>({
    outputSchema: null,
    synthesisTemplate: "",
    synthesisEnabled: false,
  });
  const [pristine, setPristine] = useState<FormState>(form);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const enableId = useId();
  const tokenPaths = useMemo(
    () => DEFAULT_TOKEN_REGISTRY.map((tok) => tok.name),
    []
  );

  useEffect(() => {
    void loadConfig(workflowId);
  }, [workflowId, loadConfig]);

  useEffect(() => {
    if (initialConfig) {
      const next: FormState = {
        outputSchema:
          (initialConfig.outputSchema as JSONSchemaObject | null) ?? null,
        synthesisTemplate: initialConfig.synthesisTemplate ?? "",
        synthesisEnabled: !!initialConfig.synthesisEnabled,
      };
      setForm(next);
      setPristine(next);
    }
  }, [initialConfig]);

  const dirty = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(pristine),
    [form, pristine]
  );

  const save = async () => {
    const result = await updateConfig(workflowId, {
      output_schema:
        form.outputSchema === null
          ? null
          : (form.outputSchema as unknown as Record<string, unknown>),
      synthesis_template: form.synthesisTemplate || null,
      synthesis_enabled: form.synthesisEnabled,
    });
    if (result) {
      setSavedAt(Date.now());
      setPristine(form);
    }
  };

  useImperativeHandle(ref, () => ({ save }));

  if (isLoading && !initialConfig) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        {t("loading")}
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-24">
      <section className="flex items-start justify-between gap-6 rounded-md border bg-card p-4 ring-1 ring-foreground/5">
        <div>
          <Label htmlFor={enableId} className="text-sm font-medium">
            {t("enableLabel")}
          </Label>
          <p className="mt-1 text-xs text-muted-foreground/80">
            {t.rich("enableHint", {
              code: (chunks) => <code className="font-mono">{chunks}</code>,
            })}
          </p>
        </div>
        <Switch
          id={enableId}
          checked={form.synthesisEnabled}
          onCheckedChange={(v) =>
            setForm((s) => ({ ...s, synthesisEnabled: v }))
          }
        />
      </section>

      <OutputSchemaEditor
        value={form.outputSchema}
        onChange={(schema) =>
          setForm((s) => ({ ...s, outputSchema: schema }))
        }
        errorMessage={error}
      />

      <section className="grid gap-6 md:grid-cols-[1fr_220px]">
        <div className="space-y-3">
          <header>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
              {t("templateTitle")}
            </p>
            <p className="mt-1 text-sm text-muted-foreground/90">
              {t.rich("templateDescription", {
                example: "{{name}}",
                code: (chunks) => (
                  <code className="font-mono text-xs">{chunks}</code>
                ),
              })}
            </p>
          </header>
          <MarkdownRichEditor
            value={form.synthesisTemplate}
            onChange={(value) =>
              setForm((s) => ({ ...s, synthesisTemplate: value }))
            }
            placeholder={t("templatePlaceholder")}
            minHeight={180}
            paths={tokenPaths}
          />
        </div>
        <TokenChipPalette
          tokens={DEFAULT_TOKEN_REGISTRY}
          onInsert={(token) =>
            setForm((s) => ({
              ...s,
              synthesisTemplate: appendAtEnd(s.synthesisTemplate, token),
            }))
          }
        />
      </section>

      {error && !isSaving ? (
        <Alert variant="destructive">
          <AlertTitle>{t("saveErrorTitle")}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {dirty || isSaving ? (
        <div
          className={cn(
            "fixed inset-x-0 bottom-0 z-10 border-t bg-background/95 backdrop-blur",
            "px-6 py-3"
          )}
        >
          <div className="mx-auto flex max-w-5xl items-center justify-end gap-3">
            <p className="text-xs text-muted-foreground">{t("unsaved")}</p>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setForm(pristine);
              }}
              disabled={isSaving}
            >
              {t("discard")}
            </Button>
            <ActionButton
              size="sm"
              onClick={save}
              loading={isSaving}
              icon={<Check className="size-3" />}
            >
              {t("save")}
            </ActionButton>
          </div>
        </div>
      ) : savedAt ? (
        <p className="text-xs text-muted-foreground/80">
          {t("savedAt", {
            time: new Date(savedAt).toLocaleTimeString(
              locale === "es" ? "es-CL" : "en-US",
              { hour: "2-digit", minute: "2-digit" }
            ),
          })}
        </p>
      ) : null}
    </div>
  );
});

function appendAtEnd(current: string, token: string): string {
  if (!current) return token;
  if (current.endsWith(" ") || current.endsWith("\n"))
    return `${current}${token}`;
  return `${current} ${token}`;
}
