"use client";

import { FileSearch, GitCompare, Info, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";

interface AnalysisConfigFormProps {
  workflowSlug: string;
}

export function AnalysisConfigForm({ workflowSlug }: AnalysisConfigFormProps) {
  const t = useTranslations("AnalysisConfig");
  const [enableAnalysis, setEnableAnalysis] = useState(true);
  const [autoValidation, setAutoValidation] = useState(false);
  const [crossDocumentValidation, setCrossDocumentValidation] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleToggleChange = (callback: (value: boolean) => void) => {
    return (checked: boolean) => {
      callback(checked);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    };
  };

  const handleContactSupport = () => {
    window.open("https://llamit.ai/contact", "_blank");
  };

  return (
    <div className="flex flex-col gap-8">
      {saved && (
        <div className="absolute top-4 right-16 flex items-center gap-2 text-green-500 text-sm font-medium">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          {t("saved")}
        </div>
      )}

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <GitCompare className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("enableTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("enableDescription")}
              </p>
            </div>
            <Switch
              checked={enableAnalysis}
              onCheckedChange={handleToggleChange(setEnableAnalysis)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <Zap className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("autoValidationTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("autoValidationDescription")}
              </p>
            </div>
            <Switch
              checked={autoValidation}
              onCheckedChange={handleToggleChange(setAutoValidation)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <FileSearch className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("crossDocTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("crossDocDescription")}
              </p>
            </div>
            <Switch
              checked={crossDocumentValidation}
              onCheckedChange={handleToggleChange(setCrossDocumentValidation)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/50 border border-border">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-background border border-border">
          <Info className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <h3 className="text-base font-semibold">{t("rulesTitle")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("rulesDescription")}
            </p>
            <div className="mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleContactSupport}
              >
                {t("configureRules")}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-base font-semibold mb-4">{t("docTypesTitle")}</h3>
        <p className="text-sm text-muted-foreground mb-4">
          {t("docTypesDescription")}
        </p>
        <div className="flex flex-col gap-2 p-4 rounded-lg bg-muted/30 border border-border">
          <p className="text-sm text-muted-foreground">{t("customRulesText")}</p>
          <div className="mt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleContactSupport}
              className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 p-0 h-auto font-normal"
            >
              {t("contactSupport")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
