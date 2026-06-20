"use client";

import { Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type { ValidationRule } from "@/src/domain/entities/doctype";
import { Button } from "@/src/presentation/components/ui/button";
import { MarkdownRichEditor } from "@/src/presentation/components/ui/markdown-rich-editor";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

interface ValidationRuleDetailProps {
  rule: ValidationRule;
  onBack: () => void;
  onUpdate?: (rule: ValidationRule) => void;
  onSave?: () => void | Promise<void>;
  fieldPaths?: string[];
}

export function ValidationRuleDetail({
  rule,
  onBack,
  onUpdate,
  onSave,
  fieldPaths = [],
}: ValidationRuleDetailProps) {
  const t = useTranslations("ValidationRuleDetail");
  const [name, setName] = useState(rule.name || "");
  const [prompt, setPrompt] = useState(rule.prompt || "");
  const [enabled, setEnabled] = useState(rule.enabled);
  const [missingDataHandling, setMissingDataHandling] = useState(
    rule.missingDataHandling || "skip"
  );

  const handleNameChange = (value: string) => {
    setName(value);
    onUpdate?.({ ...rule, name: value });
  };

  const handleEnabledChange = (checked: boolean) => {
    setEnabled(checked);
    onUpdate?.({ ...rule, enabled: checked });
  };

  const handlePromptChange = (value: string) => {
    setPrompt(value);
    onUpdate?.({ ...rule, prompt: value });
  };

  const handleMissingDataChange = (value: string | null) => {
    if (!value) return;
    const v = value as "skip" | "fail" | "pass" | "ignore";
    setMissingDataHandling(v);
    onUpdate?.({ ...rule, missingDataHandling: v });
  };

  const handleSave = async () => {
    await onSave?.();
    onBack();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-2.5">
          <label
            className="text-sm font-medium"
            htmlFor="validation-rule-name"
          >
            {t("name")}
          </label>
          <input
            id="validation-rule-name"
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder={t("namePlaceholder")}
            className="w-full rounded-md border border-input bg-white px-3 py-2 text-sm outline-none focus-visible:border-primary/40 placeholder:text-muted-foreground/70 dark:bg-input/30"
          />
        </div>

        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-medium">{t("prompt")}</label>
          <MarkdownRichEditor
            value={prompt}
            onChange={handlePromptChange}
            placeholder={t("promptPlaceholder")}
            minHeight={180}
            paths={fieldPaths}
          />
          <p className="text-xs text-muted-foreground">
            {t.rich("promptHint", {
              open: "{{",
              example: "{{persona.nombres}}",
              code: (chunks) => <code>{chunks}</code>,
            })}
          </p>
        </div>

        <div className="flex items-center justify-between gap-2">
          <Button variant="secondary" size="sm" className="gap-2">
            <Sparkles className="h-4 w-4" />
            {t("generate")}
          </Button>
          <div className="flex items-center gap-2">
            <span className="text-sm">{t("enabled")}</span>
            <Switch checked={enabled} onCheckedChange={handleEnabledChange} />
          </div>
        </div>

        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-medium">
            {t("missingData.title")}
          </label>
          <Select
            value={missingDataHandling}
            onValueChange={handleMissingDataChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="skip">
                <div className="flex flex-col gap-1 py-1">
                  <span className="font-medium">
                    {t("missingData.skip")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t("missingData.skipDescription")}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="fail">
                <div className="flex flex-col gap-1 py-1">
                  <span className="font-medium">
                    {t("missingData.fail")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t("missingData.failDescription")}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="pass">
                <div className="flex flex-col gap-1 py-1">
                  <span className="font-medium">
                    {t("missingData.pass")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t("missingData.passDescription")}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="ignore">
                <div className="flex flex-col gap-1 py-1">
                  <span className="font-medium">
                    {t("missingData.ignore")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t("missingData.ignoreDescription")}
                  </span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-border/50 px-4 py-3 bg-background">
        <Button variant="secondary" onClick={onBack}>
          {t("cancel")}
        </Button>
        <Button onClick={handleSave}>{t("save")}</Button>
      </div>
    </div>
  );
}
