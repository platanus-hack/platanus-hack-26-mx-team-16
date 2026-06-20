"use client";

import { Mail, Puzzle } from "lucide-react";
import { useTranslations } from "next-intl";
import { FaWhatsapp } from "react-icons/fa";

import {
  type WorkflowConfigStep,
  WorkflowConfigStepType,
} from "@/src/domain/entities/workflow-config";
import { Button } from "@/src/presentation/components/ui/button";
import { Card } from "@/src/presentation/components/ui/card";

interface WorkflowUploadCardProps {
  step: WorkflowConfigStep;
  onConfigure: (stepUuid: string) => void;
}

const stepIcons: Record<WorkflowConfigStepType, any> = {
  [WorkflowConfigStepType.EMAIL_UPLOAD]: Mail,
  [WorkflowConfigStepType.WHATSAPP_UPLOAD]: FaWhatsapp,
  [WorkflowConfigStepType.INTEGRATIONS]: Puzzle,
  [WorkflowConfigStepType.PRE_PROCESSING]: Mail,
  [WorkflowConfigStepType.SPLITTING]: Mail,
  [WorkflowConfigStepType.CLASSIFICATION]: Mail,
  [WorkflowConfigStepType.EXTRACTION]: Mail,
  [WorkflowConfigStepType.VALIDATION]: Mail,
  [WorkflowConfigStepType.ANALYSIS]: Mail,
  [WorkflowConfigStepType.DATA_EXPORT]: Mail,
};

export function WorkflowUploadCard({
  step,
  onConfigure,
}: WorkflowUploadCardProps) {
  const t = useTranslations("WorkflowStepCard");
  const Icon = stepIcons[step.type];

  return (
    <Card className="relative border border-border bg-card rounded-lg flex flex-col items-center justify-center gap-2">
      <div className="flex flex-col items-center gap-2 flex-1 justify-center">
        <div className="flex shrink-0 items-center justify-center mb-2">
          <Icon className="size-6 text-foreground" />
        </div>
        <div className="flex flex-col gap-1 text-center">
          <h3 className="text-base font-semibold">{step.title}</h3>
          <p className="text-sm text-muted-foreground">{step.description}</p>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onConfigure(step.uuid)}
        className="text-blue-500 hover:text-blue-600 hover:bg-blue-50"
      >
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
        {t("configure")}
      </Button>
    </Card>
  );
}
