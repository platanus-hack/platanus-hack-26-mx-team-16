import type { RecentDocument } from "@/src/domain/entities/dashboard/overview";
import {
  Avatar,
  AvatarFallback,
} from "@/src/presentation/components/ui/avatar";

interface RecentDocumentsProps {
  documents: RecentDocument[];
}

function initialsFor(name: string): string {
  const cleaned = name.replace(/\.[^.]+$/, "").trim();
  const words = cleaned.split(/[\s_-]+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export function RecentDocuments({ documents }: RecentDocumentsProps) {
  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No recent documents yet.</p>
    );
  }

  return (
    <div className="space-y-8">
      {documents.map((doc) => (
        <div key={doc.uuid} className="flex items-center">
          <Avatar className="h-9 w-9">
            <AvatarFallback>{initialsFor(doc.name)}</AvatarFallback>
          </Avatar>
          <div className="ml-4 space-y-1 min-w-0">
            <p className="text-sm font-medium leading-none truncate">
              {doc.name}
            </p>
            <p className="text-sm text-muted-foreground truncate">
              {doc.workflowName}
            </p>
          </div>
          <div className="ml-auto font-medium text-sm whitespace-nowrap">
            {doc.pageCount !== null ? `${doc.pageCount} pages` : "—"}
          </div>
        </div>
      ))}
    </div>
  );
}
