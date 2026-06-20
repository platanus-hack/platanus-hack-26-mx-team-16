"use client";

import { Copy, FileText, Layers } from "lucide-react";
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

interface PreprocessingConfigFormProps {
  workflowSlug: string;
}

type OCRMode = "skip" | "auto-detect" | "partial" | "always-full";
type ReadingOrderMode = "default" | "custom";

export function PreprocessingConfigForm({
  workflowSlug,
}: PreprocessingConfigFormProps) {
  const t = useTranslations("PreprocessingConfig");
  const [ocrMode, setOcrMode] = useState<OCRMode>("auto-detect");
  const [removeDuplicates, setRemoveDuplicates] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [readingOrderMode, setReadingOrderMode] =
    useState<ReadingOrderMode>("default");
  const [splitWords, setSplitWords] = useState(true);

  const ocrOptions = [
    {
      value: "skip" as OCRMode,
      label: t("ocr.skipLabel"),
      description: t("ocr.skipDescription"),
    },
    {
      value: "auto-detect" as OCRMode,
      label: t("ocr.autoLabel"),
      description: t("ocr.autoDescription"),
    },
    {
      value: "partial" as OCRMode,
      label: t("ocr.partialLabel"),
      description: t("ocr.partialDescription"),
    },
    {
      value: "always-full" as OCRMode,
      label: t("ocr.fullLabel"),
      description: t("ocr.fullDescription"),
    },
  ];

  const readingOrderOptions = [
    {
      value: "default" as ReadingOrderMode,
      label: t("readingOrder.defaultLabel"),
      description: t("readingOrder.defaultDescription"),
    },
    {
      value: "custom" as ReadingOrderMode,
      label: t("readingOrder.customLabel"),
      description: t("readingOrder.customDescription"),
    },
  ];

  const handleContactSupport = () => {
    window.open("https://llamit.ai/contact", "_blank");
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <FileText className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">{t("ocrTitle")}</h3>
              <p className="text-sm text-muted-foreground">
                {t("ocrDescription")}
              </p>
            </div>
            <Select
              value={ocrMode}
              onValueChange={(value: string | string[] | null) => {
                if (typeof value === "string") {
                  setOcrMode(value as OCRMode);
                } else if (Array.isArray(value) && value.length > 0) {
                  setOcrMode(value[0] as OCRMode);
                }
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue
                  placeholder={
                    ocrOptions.find((o) => o.value === ocrMode)?.label
                  }
                />
              </SelectTrigger>
              <SelectContent className="min-w-[400px] max-w-[500px]">
                {ocrOptions.map((option) => (
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

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <Copy className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("duplicatesTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("duplicatesDescription")}
              </p>
            </div>
            <Switch
              checked={removeDuplicates}
              onCheckedChange={setRemoveDuplicates}
            />
          </div>
        </div>
      </div>

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
                  className="text-muted-foreground"
                >
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
                  <path d="M9 10h6" />
                </svg>
              </div>
              <div className="flex-1 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold mb-1">
                      {t("readingOrderTitle")}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {t("readingOrderDescription")}
                    </p>
                  </div>
                  <Select
                    value={readingOrderMode}
                    onValueChange={(value: string | string[] | null) => {
                      if (typeof value === "string") {
                        setReadingOrderMode(value as ReadingOrderMode);
                      } else if (Array.isArray(value) && value.length > 0) {
                        setReadingOrderMode(value[0] as ReadingOrderMode);
                      }
                    }}
                  >
                    <SelectTrigger className="w-[180px]">
                      <SelectValue
                        placeholder={
                          readingOrderOptions.find(
                            (o) => o.value === readingOrderMode
                          )?.label
                        }
                      />
                    </SelectTrigger>
                    <SelectContent className="min-w-[400px] max-w-[500px]">
                      {readingOrderOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <div className="flex flex-col gap-1 py-1.5">
                            <span className="font-medium">{option.label}</span>
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
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
                <Layers className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold mb-1">
                      {t("splitWordsTitle")}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {t("splitWordsDescription")}
                    </p>
                  </div>
                  <Switch
                    checked={splitWords}
                    onCheckedChange={setSplitWords}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
