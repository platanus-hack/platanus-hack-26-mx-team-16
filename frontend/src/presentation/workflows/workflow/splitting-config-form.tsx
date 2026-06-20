"use client";

import { FileText, Scissors, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

interface SplittingConfigFormProps {
  workflowSlug: string;
}

type SplitterType = "general" | "custom";

export function SplittingConfigForm({
  workflowSlug,
}: SplittingConfigFormProps) {
  const t = useTranslations("SplittingConfig");
  const [autoSplit, setAutoSplit] = useState(false);
  const [splitterType, setSplitterType] = useState<SplitterType>("general");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saved, setSaved] = useState(false);

  const splitterOptions = [
    {
      value: "general" as SplitterType,
      label: t("splitters.generalLabel"),
      description: "",
    },
    {
      value: "custom" as SplitterType,
      label: t("splitters.customLabel"),
      description: t("splitters.customDescription"),
    },
  ];

  const handleContactSupport = () => {
    window.open("https://llamit.ai/contact", "_blank");
  };

  const handleToggleChange = (checked: boolean) => {
    setAutoSplit(checked);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSplitterChange = (value: string | string[] | null) => {
    if (typeof value === "string") {
      setSplitterType(value as SplitterType);
    } else if (Array.isArray(value) && value.length > 0) {
      setSplitterType(value[0] as SplitterType);
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
          <FileText className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("autoSplitTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("autoSplitDescription")}
              </p>
            </div>
            <Switch checked={autoSplit} onCheckedChange={handleToggleChange} />
          </div>
        </div>
      </div>

      {autoSplit && (
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Scissors className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h3 className="text-base font-semibold mb-1">
                  {t("selectSplitterTitle")}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {t("selectSplitterDescription")}
                </p>
              </div>
              <Select value={splitterType} onValueChange={handleSplitterChange}>
                <SelectTrigger className="w-[220px]">
                  <SelectValue placeholder={t("chooseSplitter")} />
                </SelectTrigger>
                <SelectContent className="min-w-[300px] max-w-[400px]">
                  {splitterOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex flex-col gap-1 py-1.5">
                        <span className="font-medium">{option.label}</span>
                        {option.description && (
                          <>
                            <span className="text-xs text-muted-foreground font-normal whitespace-normal leading-relaxed">
                              {option.description}
                            </span>
                            {option.value === "custom" && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleContactSupport();
                                }}
                                className="mt-2 w-fit"
                              >
                                {t("contactSupport")}
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <Button
          variant="link"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-blue-500 hover:text-blue-600 p-0 h-auto font-normal"
        >
          {showAdvanced ? t("hideAdvanced") : t("showAdvanced")}
        </Button>
      </div>

      {showAdvanced && (
        <div className="border-t pt-6">
          <h3 className="text-base font-semibold mb-6">
            {t("advancedTitle")}
          </h3>

          <div className="flex flex-col gap-8">
            <div className="flex items-start gap-3">
              <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
                <Sparkles className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold mb-1">
                      {t("customSplittersTitle")}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {t("customSplittersDescription")}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleContactSupport}
                  >
                    {t("contactSupport")}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
