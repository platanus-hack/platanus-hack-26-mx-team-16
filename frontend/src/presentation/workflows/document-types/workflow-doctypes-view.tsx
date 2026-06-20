"use client";

import { FileText } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  useCreateDocumentTypeMutation,
  useDeleteDocumentTypeMutation,
  useDocumentTypesQuery,
} from "@/src/application/hooks/queries/document-types";
import type { DocumentType } from "@/src/domain/entities/doctype";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
import { DocumentTypeCard } from "@/src/presentation/workflows/document-types/document-type-card";

export function WorkflowDocumentTypesView() {
  const t = useTranslations("DocumentTypes");
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;

  const [documentTypeToDelete, setDocumentTypeToDelete] =
    useState<DocumentType | null>(null);

  const { data: documentTypes = [], isLoading } = useDocumentTypesQuery(wfSlug);
  const createMutation = useCreateDocumentTypeMutation(wfSlug);
  const deleteMutation = useDeleteDocumentTypeMutation(wfSlug);

  const handleAddDocumentType = async () => {
    const doctype = await createMutation.mutateAsync({ name: "Untitled" });
    router.push(`/workflows/${wfSlug}/document-types/${doctype.uuid}`);
  };

  const handleDuplicate = async (uuid: string) => {
    const documentType = documentTypes.find(
      (dt: DocumentType) => dt.uuid === uuid
    );
    if (!documentType) return;
    await createMutation.mutateAsync({
      name: `${documentType.name} ${t("duplicateSuffix")}`,
      description: documentType.description,
    });
  };

  const confirmDelete = async () => {
    if (!documentTypeToDelete) return;
    await deleteMutation.mutateAsync(documentTypeToDelete.uuid);
    setDocumentTypeToDelete(null);
  };

  if (isLoading) return <FullPageSpinner />;

  return (
    <div className="flex flex-col flex-1 h-full">
      <div className="flex-1 flex flex-col overflow-auto">
        {documentTypes.length === 0 ? (
          <div className="flex flex-1 items-center justify-center h-full">
            <EmptyState
              icon={FileText}
              title={t("emptyTitle")}
              description={t("emptyDescriptionAdd")}
              actionLabel={t("addCta")}
              onAction={handleAddDocumentType}
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documentTypes.map((documentType: DocumentType) => (
              <DocumentTypeCard
                key={documentType.uuid}
                doctype={documentType}
                onCopyId={(uuid) => navigator.clipboard.writeText(uuid)}
                onDuplicate={handleDuplicate}
                onSettings={(uuid) =>
                  router.push(`/workflows/${wfSlug}/document-types/${uuid}`)
                }
                onDelete={(uuid) => {
                  const dt = documentTypes.find(
                    (d: DocumentType) => d.uuid === uuid
                  );
                  if (dt) setDocumentTypeToDelete(dt);
                }}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDeleteDialog
        open={documentTypeToDelete !== null}
        onOpenChange={(open) => {
          if (!open) setDocumentTypeToDelete(null);
        }}
        onConfirm={confirmDelete}
        title={t("deleteTitle")}
        description={t("deleteDescription", {
          name: documentTypeToDelete?.name ?? "",
        })}
        confirmLabel={t("delete")}
        cancelLabel={t("cancel")}
      />
    </div>
  );
}
