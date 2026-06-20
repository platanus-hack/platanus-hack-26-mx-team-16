"use client";

import { FileX, Network, Zap } from "lucide-react";
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

interface ClassificationConfigFormProps {
  workflowSlug: string;
}

type ClassificationModelType = "default" | "fast-recruit";

export function ClassificationConfigForm({
  workflowSlug,
}: ClassificationConfigFormProps) {
  const t = useTranslations("ClassificationConfig");
  const [autoClassification, setAutoClassification] = useState(true);
  const [rejectDocuments, setRejectDocuments] = useState(false);
  const [classificationModel, setClassificationModel] =
    useState<ClassificationModelType>("default");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saved, setSaved] = useState(false);

  const classificationModelOptions = [
    {
      value: "default" as ClassificationModelType,
      label: t("models.defaultLabel"),
      description: t("models.defaultDescription"),
    },
    {
      value: "fast-recruit" as ClassificationModelType,
      label: t("models.fastLabel"),
      description: t("models.fastDescription"),
    },
  ];

  const handleToggleChange = (callback: (value: boolean) => void) => {
    return (checked: boolean) => {
      callback(checked);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    };
  };

  const handleModelChange = (value: string | string[] | null) => {
    if (typeof value === "string") {
      setClassificationModel(value as ClassificationModelType);
    } else if (Array.isArray(value) && value.length > 0) {
      setClassificationModel(value[0] as ClassificationModelType);
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
          <Zap className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">{t("autoTitle")}</h3>
              <p className="text-sm text-muted-foreground">
                {t("autoDescription")}
              </p>
            </div>
            <Switch
              checked={autoClassification}
              onCheckedChange={handleToggleChange(setAutoClassification)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
          <FileX className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold mb-1">
                {t("rejectTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("rejectDescription")}
              </p>
            </div>
            <Switch
              checked={rejectDocuments}
              onCheckedChange={handleToggleChange(setRejectDocuments)}
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
                <Network className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold mb-1">
                      {t("modelTitle")}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {t("modelDescription")}
                    </p>
                  </div>
                  <Select
                    value={classificationModel}
                    onValueChange={handleModelChange}
                  >
                    <SelectTrigger className="w-[220px]">
                      <SelectValue placeholder={t("models.defaultLabel")} />
                    </SelectTrigger>
                    <SelectContent className="min-w-[400px] max-w-[500px]">
                      {classificationModelOptions.map((option) => (
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
      )}
    </div>
  );
}
