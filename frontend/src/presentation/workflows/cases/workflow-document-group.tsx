"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { cn } from "@/src/application/lib/utils";
import type { CaseDocumentGroup } from "@/src/domain/entities/case";
import { DocumentTypeCard } from "./cards/document-type";
import { WorkflowDocumentCard } from "./cards/workflow-document";

interface WorkflowDocumentGroupContainerProps {
  workflowUuid: string;
  caseId: string;
  group: CaseDocumentGroup;
  reExtractingDocumentIds?: Set<string>;
  onDocumentsChanged: () => Promise<void>;
}

const MAX_VISIBLE_STACK_DEPTH = 3;

export function WorkflowDocumentGroupContainer({
  workflowUuid,
  caseId,
  group,
  reExtractingDocumentIds,
  onDocumentsChanged,
}: WorkflowDocumentGroupContainerProps) {
  const t = useTranslations("DocumentGroup");
  const [activeIdx, setActiveIdx] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  const { documentType, documents } = group;

  const isReExtractingDoc = (doc: { uuid: string } | undefined) =>
    Boolean(doc?.uuid && reExtractingDocumentIds?.has(doc.uuid));

  if (documents.length === 0) {
    return (
      <DocumentTypeCard
        workflowUuid={workflowUuid}
        caseId={caseId}
        documentType={documentType}
        document={null}
        onDocumentsChanged={onDocumentsChanged}
      />
    );
  }

  // Active card at front (stackPos=0), rest behind it preserving original order.
  const safeActive = Math.min(activeIdx, documents.length - 1);
  const ordered = [
    documents[safeActive],
    ...documents.slice(0, safeActive),
    ...documents.slice(safeActive + 1),
  ];

  return (
    <div
      className="relative"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Layout spacer keeps grid cell height since real cards are absolute. */}
      <div className="invisible pointer-events-none">
        <WorkflowDocumentCard
          workflowUuid={workflowUuid}
          caseId={caseId}
          documentType={documentType}
          document={ordered[0]}
          isReExtracting={isReExtractingDoc(ordered[0])}
          onDocumentsChanged={onDocumentsChanged}
        />
      </div>

      {ordered.map((doc, stackPos) => {
        const depth = Math.min(stackPos, MAX_VISIBLE_STACK_DEPTH);
        const base = depth * 6;
        const fanOut = depth * 18;
        const translateX = isHovered ? fanOut : base;
        const translateY = isHovered ? depth * 2 : base;
        const rotate = depth * 1.2;
        return (
          <div
            key={doc.uuid}
            style={{
              zIndex: ordered.length - stackPos,
              transform: `translate(${translateX}px, ${translateY}px) rotate(${rotate}deg)`,
              transformOrigin: "top left",
            }}
            className={cn(
              "absolute inset-0 transition-transform duration-200 ease-out",
              stackPos > MAX_VISIBLE_STACK_DEPTH &&
                "opacity-0 pointer-events-none"
            )}
          >
            {stackPos === 0 ? (
              <WorkflowDocumentCard
                workflowUuid={workflowUuid}
                caseId={caseId}
                documentType={documentType}
                document={doc}
                isReExtracting={isReExtractingDoc(doc)}
                onDocumentsChanged={onDocumentsChanged}
              />
            ) : (
              <>
                <div className="pointer-events-none">
                  <WorkflowDocumentCard
                    workflowUuid={workflowUuid}
                    caseId={caseId}
                    documentType={documentType}
                    document={doc}
                    isReExtracting={isReExtractingDoc(doc)}
                    onDocumentsChanged={onDocumentsChanged}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const origIdx = documents.findIndex(
                      (d) => d.uuid === doc.uuid
                    );
                    if (origIdx !== -1) setActiveIdx(origIdx);
                  }}
                  aria-label={t("bringToFront", {
                    name: doc.fileName ?? t("fallbackName"),
                  })}
                  className="absolute inset-0 cursor-pointer rounded-xl focus-visible:ring-2 focus-visible:ring-primary/40"
                />
              </>
            )}
          </div>
        );
      })}

      <div
        aria-hidden
        className="absolute -top-2 -right-2 z-[100] rounded-full bg-primary text-primary-foreground text-xs font-semibold px-2.5 py-0.5 shadow-md pointer-events-none"
      >
        {documents.length}
      </div>
    </div>
  );
}
