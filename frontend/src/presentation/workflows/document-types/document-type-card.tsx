import {
  Copy,
  FileText,
  List,
  MoreVertical,
  Settings,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { stripMarkdown } from "@/src/application/lib/strip-markdown";
import type { DocumentType } from "@/src/domain/entities/doctype";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/src/presentation/components/ui/dropdown-menu";

interface DocumentTypeCardProps {
  doctype: DocumentType;
  onCopyId: (uuid: string) => void;
  onDuplicate: (uuid: string) => void;
  onSettings: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}

export function DocumentTypeCard({
  doctype,
  onCopyId,
  onDuplicate,
  onSettings,
  onDelete,
}: DocumentTypeCardProps) {
  const t = useTranslations("DocumentTypeCard");
  const router = useRouter();
  const params = useParams();
  const wfSlug = params.wfSlug as string;

  const handleCardClick = () => {
    router.push(`/workflows/${wfSlug}/document-types/${doctype.uuid}`);
  };

  const schemaProps = (
    doctype.fields as { properties?: Record<string, unknown> } | undefined
  )?.properties;
  const fieldsCount =
    schemaProps && typeof schemaProps === "object"
      ? Object.keys(schemaProps).length
      : 0;
  const validationsCount = doctype.validationRules?.length ?? 0;
  const descriptionText = stripMarkdown(doctype.description);

  return (
    <Card
      className="cursor-pointer border border-border ring-0 transition-all duration-200 hover:shadow-md hover:bg-muted/30"
      onClick={handleCardClick}
    >
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="mt-1">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <CardTitle className="mb-2">{doctype.name}</CardTitle>
            {descriptionText && (
              <p
                className="text-sm text-muted-foreground leading-relaxed line-clamp-3"
                title={descriptionText}
              >
                {descriptionText}
              </p>
            )}
          </div>
        </div>
        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger
              className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onCopyId(doctype.uuid);
                }}
              >
                <Copy className="mr-2 h-4 w-4" />
                {t("copyId")}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onDuplicate(doctype.uuid);
                }}
              >
                <Copy className="mr-2 h-4 w-4" />
                {t("duplicate")}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onSettings(doctype.uuid);
                }}
              >
                <Settings className="mr-2 h-4 w-4" />
                {t("settings")}
              </DropdownMenuItem>
              <DropdownMenuItem
                variant="destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(doctype.uuid);
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t("delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <List className="h-3.5 w-3.5" />
            <span>
              {fieldsCount === 1
                ? t("fieldOne", { count: fieldsCount })
                : t("fieldOther", { count: fieldsCount })}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span
              className={validationsCount > 0 ? "text-emerald-500" : undefined}
            >
              {validationsCount === 1
                ? t("validationOne", { count: validationsCount })
                : t("validationOther", { count: validationsCount })}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
