"use client";

import { useParams } from "next/navigation";
import { DocumentDetailView } from "../../../../../../presentation/workflows/documents/document-detail-view";
import { DocumentShell } from "../../../../../../presentation/workflows/documents/document-shell";

export default function DocumentDetailPage() {
  const params = useParams();
  const documentId = params.documentId as string;

  return (
    <DocumentShell>
      <DocumentDetailView documentId={documentId} />
    </DocumentShell>
  );
}
