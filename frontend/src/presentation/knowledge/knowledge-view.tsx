"use client";

import { Database, Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  useDeleteKnowledgeBaseMutation,
  useDuplicateKnowledgeBaseMutation,
  useKnowledgeBasesQuery,
} from "@/src/application/hooks/queries/knowledge";
import type { Knowledge } from "@/src/domain/entities/knowledge";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Button } from "@/src/presentation/components/ui/button";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
import { KnowledgeCard } from "./knowledge-card";

export function KnowledgeView() {
  const t = useTranslations("Knowledge");
  const { data: knowledgeList = [], isLoading } = useKnowledgeBasesQuery();
  const duplicateMutation = useDuplicateKnowledgeBaseMutation();
  const deleteMutation = useDeleteKnowledgeBaseMutation();

  const handleCreateKnowledge = () => {
    console.log("Create knowledge");
  };

  if (isLoading) return <FullPageSpinner />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
        <Button onClick={handleCreateKnowledge} className="gap-2">
          <Plus className="h-4 w-4" />
          {t("create")}
        </Button>
      </div>

      {knowledgeList.length === 0 ? (
        <EmptyState
          icon={Database}
          title={t("emptyTitle")}
          description={t("emptyDescription")}
          actionLabel={t("newCta")}
          onAction={handleCreateKnowledge}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {knowledgeList.map((knowledge: Knowledge) => (
            <KnowledgeCard
              key={knowledge.uuid}
              knowledge={knowledge}
              onCopyId={(uuid) => navigator.clipboard.writeText(uuid)}
              onDuplicate={(uuid) => duplicateMutation.mutate(uuid)}
              onSettings={(uuid) => console.log("Open settings for:", uuid)}
              onDelete={(uuid) => deleteMutation.mutate(uuid)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
