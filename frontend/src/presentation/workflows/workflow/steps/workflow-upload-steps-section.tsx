import { WorkflowUploadCard } from "../workflow-upload-card";
import { WorkflowArrow } from "../workflow-arrow";
import type { WorkflowConfigStep } from "@/src/domain/entities/workflow-config";

interface WorkflowUploadStepsSectionProps {
  steps: WorkflowConfigStep[];
  showArrow?: boolean;
  onConfigure: (stepUuid: string) => void;
}

export function WorkflowUploadStepsSection({
  steps,
  showArrow = true,
  onConfigure,
}: WorkflowUploadStepsSectionProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <>
      <div className="grid grid-cols-3 gap-4 w-full">
        {steps.map((step) => (
          <WorkflowUploadCard
            key={step.uuid}
            step={step}
            onConfigure={onConfigure}
          />
        ))}
      </div>
      {showArrow && <WorkflowArrow />}
    </>
  );
}
