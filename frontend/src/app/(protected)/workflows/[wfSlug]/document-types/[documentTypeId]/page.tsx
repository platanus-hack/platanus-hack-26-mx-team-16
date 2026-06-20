"use client";

import { use } from "react";
import { DocumentTypeDetailView } from "@/src/presentation/workflows/document-types/detail/doctype-detail-view";

interface WorkflowDocumentTypeDetailPageProps {
  params: Promise<{ wfSlug: string; documentTypeId: string }>;
}

export default function WorkflowDocumentTypeDetailPage({
  params,
}: WorkflowDocumentTypeDetailPageProps) {
  const { documentTypeId } = use(params);

  return <DocumentTypeDetailView doctypeId={documentTypeId} />;
}
