import {
  Copy,
  FileText,
  MoreVertical,
  Settings,
  Trash2,
  Users,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { formatRelativeDate } from "@/src/application/lib/format-relative-date";
import type { Knowledge } from "@/src/domain/entities/knowledge";
import {
  Avatar,
  AvatarFallback,
} from "@/src/presentation/components/ui/avatar";
import { Badge } from "@/src/presentation/components/ui/badge";
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

interface KnowledgeCardProps {
  knowledge: Knowledge;
  onCopyId: (uuid: string) => void;
  onDuplicate: (uuid: string) => void;
  onSettings: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}

export function KnowledgeCard({
  knowledge,
  onCopyId,
  onDuplicate,
  onSettings,
  onDelete,
}: KnowledgeCardProps) {
  const t = useTranslations("KnowledgeCard");

  const getInitials = (name: string) =>
    name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);

  return (
    <Card className="cursor-pointer transition-all duration-300 hover:shadow-md hover:border-primary/20 hover:bg-muted/20">
      <CardHeader>
        <div className="flex items-start gap-3">
          <Avatar className="h-10 w-10 shrink-0">
            <AvatarFallback className="bg-primary/10 text-primary text-xs">
              {getInitials(knowledge.owner.name)}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base mb-1">{knowledge.name}</CardTitle>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <span>{knowledge.owner.name}</span>
              <span>·</span>
              <span>
                {t("editedRelative", {
                  date: formatRelativeDate(knowledge.updatedAt),
                })}
              </span>
            </div>
            {knowledge.description && (
              <p className="text-sm text-muted-foreground line-clamp-2 mt-2">
                {knowledge.description}
              </p>
            )}
          </div>
        </div>
        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors">
              <MoreVertical className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => onCopyId(knowledge.uuid)}>
                <Copy className="mr-2 h-4 w-4" />
                {t("copyId")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDuplicate(knowledge.uuid)}>
                <Copy className="mr-2 h-4 w-4" />
                {t("duplicate")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onSettings(knowledge.uuid)}>
                <Settings className="mr-2 h-4 w-4" />
                {t("settings")}
              </DropdownMenuItem>
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onDelete(knowledge.uuid)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t("delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex flex-wrap gap-2">
            {knowledge.status.length > 0
              ? knowledge.status.map((status, index) => (
                  <Badge
                    key={index}
                    variant="outline"
                    className="gap-1.5 font-normal text-xs"
                  >
                    {status}
                  </Badge>
                ))
              : null}
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              <span>{knowledge.docCount}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              <span>
                {knowledge.docCount}/{knowledge.totalDocs}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
