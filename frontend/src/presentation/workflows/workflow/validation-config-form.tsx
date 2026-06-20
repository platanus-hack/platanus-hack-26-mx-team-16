"use client";

import { AlertCircle, Eye, Network, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

interface ValidationConfigFormProps {
  workflowSlug: string;
}

type ModelMemoryMode = "auto" | "manual" | "always";

export function ValidationConfigForm({
  workflowSlug,
}: ValidationConfigFormProps) {
  const t = useTranslations("ValidationConfig");
  const [enableValidation, setEnableValidation] = useState(true);
  const [autoConfirmation, setAutoConfirmation] = useState(false);
  const [allowFailedValidation, setAllowFailedValidation] = useState(true);
  const [modelMemoryMode, setModelMemoryMode] =
    useState<ModelMemoryMode>("auto");
  const [saved, setSaved] = useState(false);

  const modelMemoryOptions = [
    {
      value: "auto" as ModelMemoryMode,
      label: t("memory.autoLabel"),
      description: t("memory.autoDescription"),
    },
    {
      value: "manual" as ModelMemoryMode,
      label: t("memory.manualLabel"),
      description: t("memory.manualDescription"),
    },
    {
      value: "always" as ModelMemoryMode,
      label: t("memory.alwaysLabel"),
      description: t("memory.alwaysDescription"),
    },
  ];

  const handleToggleChange = (callback: (value: boolean) => void) => {
    return (checked: boolean) => {
      callback(checked);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    };
  };

  const handleModelMemoryChange = (value: string | string[] | null) => {
    if (typeof value === "string") {
      setModelMemoryMode(value as ModelMemoryMode);
    } else if (Array.isArray(value) && value.length > 0) {
      setModelMemoryMode(value[0] as ModelMemoryMode);
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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
          <Eye className="h-4 w-4 text-muted-foreground" />
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
              checked={enableValidation}
              onCheckedChange={handleToggleChange(setEnableValidation)}
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
                {t("autoConfirmTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("autoConfirmDescription")}
              </p>
            </div>
            <Switch
              checked={autoConfirmation}
              onCheckedChange={handleToggleChange(setAutoConfirmation)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <AlertCircle className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("allowFailedTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("allowFailedDescription")}
              </p>
            </div>
            <Switch
              checked={allowFailedValidation}
              onCheckedChange={handleToggleChange(setAllowFailedValidation)}
            />
          </div>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-base font-semibold mb-6">{t("learningTitle")}</h3>

        <div className="flex flex-col gap-8">
          <div className="flex items-start gap-3">
            <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
              <Network className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="flex-1 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <h4 className="text-base font-semibold mb-1">
                    {t("memoryTitle")}
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    {t("memoryDescription")}
                  </p>
                </div>
                <Select
                  value={modelMemoryMode}
                  onValueChange={handleModelMemoryChange}
                >
                  <SelectTrigger className="w-[220px]">
                    <SelectValue placeholder={t("memory.autoLabel")} />
                  </SelectTrigger>
                  <SelectContent className="min-w-[400px] max-w-[500px]">
                    {modelMemoryOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex flex-col gap-1 py-1.5">
                          <span className="font-medium">{option.label}</span>
                          <span className="text-xs text-muted-foreground font-normal whitespace-normal leading-relaxed">
                            {option.description}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
