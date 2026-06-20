import { WorkflowStepCard } from "../workflow-step-card";
import { WorkflowArrow } from "../workflow-arrow";
import type { WorkflowConfigStep } from "@/src/domain/entities/workflow-config";

interface WorkflowProcessingStepsSectionProps {
  steps: WorkflowConfigStep[];
  onConfigure: (stepUuid: string) => void;
  onConfigureDocumentType: (doctypeUuid: string) => void;
  onAddDocumentType: () => void;
  onDeleteDocumentType: (doctypeUuid: string) => void;
}

export function WorkflowProcessingStepsSection({
  steps,
  onConfigure,
  onConfigureDocumentType,
  onAddDocumentType,
  onDeleteDocumentType,
}: WorkflowProcessingStepsSectionProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <>
      {steps.map((step) => (
        <div key={step.uuid} className="w-full">
          <WorkflowStepCard
            step={step}
            onConfigure={onConfigure}
            onConfigureDocumentType={onConfigureDocumentType}
            onAddDocumentType={onAddDocumentType}
            onDeleteDocumentType={onDeleteDocumentType}
          />
          <WorkflowArrow />
        </div>
      ))}
    </>
  );
}
