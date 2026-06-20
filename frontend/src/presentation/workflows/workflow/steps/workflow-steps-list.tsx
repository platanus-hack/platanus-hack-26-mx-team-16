import { WorkflowUploadStepsSection } from "./workflow-upload-steps-section";
import { WorkflowProcessingStepsSection } from "./workflow-processing-steps-section";
import {
  WorkflowConfigStepType,
  type WorkflowConfigStep,
} from "@/src/domain/entities/workflow-config";

interface WorkflowStepsListProps {
  steps: WorkflowConfigStep[];
  onConfigure: (stepUuid: string) => void;
  onConfigureDocumentType: (doctypeUuid: string) => void;
  onAddDocumentType: () => void;
  onDeleteDocumentType: (doctypeUuid: string) => void;
}

export function WorkflowStepsList({
  steps,
  onConfigure,
  onConfigureDocumentType,
  onAddDocumentType,
  onDeleteDocumentType,
}: WorkflowStepsListProps) {
  const uploadSteps = steps.filter(
    (step) =>
      step.type === WorkflowConfigStepType.EMAIL_UPLOAD ||
      step.type === WorkflowConfigStepType.WHATSAPP_UPLOAD ||
      step.type === WorkflowConfigStepType.INTEGRATIONS
  );

  const processingSteps = steps.filter(
    (step) =>
      step.type !== WorkflowConfigStepType.EMAIL_UPLOAD &&
      step.type !== WorkflowConfigStepType.WHATSAPP_UPLOAD &&
      step.type !== WorkflowConfigStepType.INTEGRATIONS
  );

  return (
    <>
      <WorkflowUploadStepsSection
        steps={uploadSteps}
        showArrow={processingSteps.length > 0}
        onConfigure={onConfigure}
      />
      <WorkflowProcessingStepsSection
        steps={processingSteps}
        onConfigure={onConfigure}
        onConfigureDocumentType={onConfigureDocumentType}
        onAddDocumentType={onAddDocumentType}
        onDeleteDocumentType={onDeleteDocumentType}
      />
    </>
  );
}
