"use client";

import type { CaseDocumentGroup } from "src/domain/entities/case";
import { WorkflowDocumentGroupContainer } from "../workflow-document-group";

interface Props {
  workflowUuid: string;
  caseId: string;
  documentGroups: CaseDocumentGroup[];
  /** WorkflowDocument uuids whose parent set is currently re-extracting (live SSE feed). */
  reExtractingDocumentIds?: Set<string>;
  onDocumentsChanged: () => Promise<void>;
}

export function WorkflowCaseDocumentsTab({
  workflowUuid,
  caseId,
  documentGroups,
  reExtractingDocumentIds,
  onDocumentsChanged,
}: Props) {
  return (
    <div className="flex flex-col gap-6 mt-6">
      {documentGroups.length === 0 ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          No hay tipos de documento configurados en este workflow.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2 pr-2">
          {documentGroups.map((group) => (
            <WorkflowDocumentGroupContainer
              key={group.documentType.uuid}
              workflowUuid={workflowUuid}
              caseId={caseId}
              group={group}
              reExtractingDocumentIds={reExtractingDocumentIds}
              onDocumentsChanged={onDocumentsChanged}
            />
          ))}
        </div>
      )}
    </div>
  );
}
