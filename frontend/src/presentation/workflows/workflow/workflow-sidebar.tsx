"use client";

import { BookOpen, ExternalLink, MessageCircle, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/src/application/lib/utils";
import {
  type WorkflowConfigStep,
  WorkflowConfigStepType,
} from "@/src/domain/entities/workflow-config";
import {
  Button,
  buttonVariants,
} from "@/src/presentation/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetFooter,
} from "@/src/presentation/components/ui/sheet";
import { AnalysisConfigForm } from "./analysis-config-form";
import { ClassificationConfigForm } from "./classification-config-form";
import { DataExportConfigForm } from "./data-export-config-form";
import { EmailUploadConfigForm } from "./email-upload-config-form";
import { IntegrationsConfigForm } from "./integrations-config-form";
import { PreprocessingConfigForm } from "./preprocessing-config-form";
import { SplittingConfigForm } from "./splitting-config-form";
import { ValidationConfigForm } from "./validation-config-form";
import { WhatsappUploadConfigForm } from "./whatsapp-upload-config-form";

interface WorkflowSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  step?: WorkflowConfigStep | null;
  workflowSlug?: string;
  children?: React.ReactNode;
}

export function WorkflowSidebar({
  open,
  onOpenChange,
  title,
  step,
  workflowSlug,
  children,
}: WorkflowSidebarProps) {
  const t = useTranslations("WorkflowSidebar");

  const renderStepContent = () => {
    if (!step) return children;

    switch (step.type) {
      case WorkflowConfigStepType.EMAIL_UPLOAD:
        return workflowSlug ? (
          <EmailUploadConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.WHATSAPP_UPLOAD:
        return workflowSlug ? (
          <WhatsappUploadConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.INTEGRATIONS:
        return workflowSlug ? (
          <IntegrationsConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.PRE_PROCESSING:
        return workflowSlug ? (
          <PreprocessingConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.SPLITTING:
        return workflowSlug ? (
          <SplittingConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.CLASSIFICATION:
        return workflowSlug ? (
          <ClassificationConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.VALIDATION:
        return workflowSlug ? (
          <ValidationConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.ANALYSIS:
        return workflowSlug ? (
          <AnalysisConfigForm workflowSlug={workflowSlug} />
        ) : null;
      case WorkflowConfigStepType.DATA_EXPORT:
        return workflowSlug ? (
          <DataExportConfigForm workflowSlug={workflowSlug} />
        ) : null;
      default:
        return children;
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="!w-[90%] md:!w-[40%] !max-w-none p-0 flex flex-col"
        showCloseButton={false}
      >
        <div className="flex items-center gap-3 p-4 border-b shrink-0">
          <SheetClose render={<Button variant="ghost" size="icon-sm" />}>
            <XIcon className="h-4 w-4" />
            <span className="sr-only">{t("close")}</span>
          </SheetClose>
          <h2 className="text-xl font-normal font-sans">{title}</h2>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-4">
          {renderStepContent()}
        </div>

        <SheetFooter className="border-t pt-4 shrink-0">
          <div className="flex flex-col gap-0 w-full">
            <a
              href="https://docs.llamit.ai"
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "justify-start gap-2 text-blue-400 hover:text-blue-500 hover:bg-blue-50"
              )}
            >
              <BookOpen className="h-4 w-4" />
              {t("readDocs")}
              <ExternalLink className="h-3 w-3 ml-auto" />
            </a>
            <a
              href="https://llamit.ai/contact"
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "justify-start gap-2 text-blue-400 hover:text-blue-500 hover:bg-blue-50"
              )}
            >
              <MessageCircle className="h-4 w-4" />
              {t("contactTeam")}
              <ExternalLink className="h-3 w-3 ml-auto" />
            </a>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
