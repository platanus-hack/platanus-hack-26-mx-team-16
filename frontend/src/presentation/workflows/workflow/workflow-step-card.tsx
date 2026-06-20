"use client";

import {
  Eye,
  FileSearch,
  FileText,
  GitCompare,
  Mail,
  Network,
  Plus,
  Puzzle,
  Scissors,
  Trash2,
  Upload,
  Zap,
} from "lucide-react";
import { useTranslations } from "next-intl";

import {
  type WorkflowConfigStep,
  WorkflowConfigStepType,
} from "@/src/domain/entities/workflow-config";
import { Button } from "@/src/presentation/components/ui/button";
import { Card } from "@/src/presentation/components/ui/card";

interface WorkflowStepCardProps {
  step: WorkflowConfigStep;
  onConfigure: (stepUuid: string) => void;
  onConfigureDocumentType?: (doctypeUuid: string) => void;
  onAddDocumentType?: () => void;
  onDeleteDocumentType?: (doctypeUuid: string) => void;
}

const stepIcons: Record<WorkflowConfigStepType, typeof Mail> = {
  [WorkflowConfigStepType.EMAIL_UPLOAD]: Mail,
  [WorkflowConfigStepType.WHATSAPP_UPLOAD]: Mail,
  [WorkflowConfigStepType.INTEGRATIONS]: Puzzle,
  [WorkflowConfigStepType.PRE_PROCESSING]: FileSearch,
  [WorkflowConfigStepType.SPLITTING]: Scissors,
  [WorkflowConfigStepType.CLASSIFICATION]: Network,
  [WorkflowConfigStepType.EXTRACTION]: Zap,
  [WorkflowConfigStepType.VALIDATION]: Eye,
  [WorkflowConfigStepType.ANALYSIS]: GitCompare,
  [WorkflowConfigStepType.DATA_EXPORT]: Upload,
};

function GearIcon() {
  return (
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
      className="mr-1.5"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function WorkflowStepCard({
  step,
  onConfigure,
  onConfigureDocumentType,
  onAddDocumentType,
  onDeleteDocumentType,
}: WorkflowStepCardProps) {
  const t = useTranslations("WorkflowStepCard");
  const Icon = stepIcons[step.type];

  return (
    <Card className="relative border border-border bg-card rounded-lg p-0">
      <div className="flex items-center gap-4 px-4 py-4">
        <div className="flex shrink-0 items-center justify-center">
          <Icon className="h-6 w-6 text-foreground" />
        </div>
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <h3 className="text-base font-semibold">{step.title}</h3>
          <p className="text-sm text-muted-foreground">{step.description}</p>
        </div>
        {step.type !== WorkflowConfigStepType.EXTRACTION && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onConfigure(step.uuid)}
            className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 shrink-0"
          >
            <GearIcon />
            {t("configure")}
          </Button>
        )}
      </div>

      {step.type === WorkflowConfigStepType.EXTRACTION &&
        step.extractionDoctypes &&
        step.extractionDoctypes.length > 0 && (
          <div className="px-6 pb-5 space-y-2.5 pt-1">
            {step.extractionDoctypes.map((doctype) => (
              <div
                key={doctype.doctype.uuid}
                className="flex items-center justify-between py-3 px-4 border border-border rounded-md bg-background"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-sm truncate">
                    {doctype.doctype.name}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{t("fields", { count: doctype.fieldsCount })}</span>
                    <span>{t("checks", { count: doctype.checksCount })}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      onConfigureDocumentType?.(doctype.doctype.uuid)
                    }
                    className="text-blue-500 hover:text-blue-600 hover:bg-blue-50"
                  >
                    <GearIcon />
                    {t("configure")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      onDeleteDocumentType?.(doctype.doctype.uuid)
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={onAddDocumentType}
              className="flex items-center justify-center w-full py-3 px-4 border-2 border-dashed border-border rounded-md hover:border-blue-500 hover:bg-blue-50/50 transition-colors"
            >
              <Plus className="h-4 w-4 text-blue-500 mr-2" />
              <span className="text-sm text-blue-500">
                {t("addDocumentType")}
              </span>
            </button>
          </div>
        )}
    </Card>
  );
}
