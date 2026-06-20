"use client";

import { FileCode, FileText, FlaskConical, Layers, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ChangeEvent, useState } from "react";

import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

export interface CreateWorkflowSubmit {
  name: string;
  // E7 · F2: receta inicial elegida (slug). null/ausente ⇒ extracción estándar.
  templateSlug?: string | null;
  // Texto YAML crudo cuando el alta arranca desde una plantilla .yml.
  yaml?: string;
}

interface CreateWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: CreateWorkflowSubmit) => Promise<void>;
}

export function CreateWorkflowDialog({
  open,
  onOpenChange,
  onSubmit,
}: CreateWorkflowDialogProps) {
  const t = useTranslations("Workflows.createDialog");
  const [name, setName] = useState("");
  // E7 · F2: receta inicial elegida (null ⇒ extracción estándar).
  const [templateSlug, setTemplateSlug] = useState<string | null>(null);
  const [yamlMode, setYamlMode] = useState(false);
  const [yamlText, setYamlText] = useState("");
  const [yamlFileName, setYamlFileName] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // E7 · F2: recetas iniciales canónicas (slug → el backend clona la receta).
  const starterRecipes = [
    {
      slug: null,
      label: t("standard"),
      description: t("standardDescription"),
      icon: FileText,
    },
    {
      slug: "standard-analysis",
      label: t("analysis"),
      description: t("analysisDescription"),
      icon: FlaskConical,
    },
    {
      slug: "standard-case",
      label: t("caseRecipe"),
      description: t("caseRecipeDescription"),
      icon: Layers,
    },
  ] as const;

  const canSubmit =
    name.trim().length > 0 &&
    !isSubmitting &&
    (!yamlMode || yamlText.trim().length > 0);

  const resetForm = () => {
    setName("");
    setTemplateSlug(null);
    setYamlMode(false);
    setYamlText("");
    setYamlFileName(null);
  };

  const selectRecipe = (slug: string | null) => {
    setYamlMode(false);
    setTemplateSlug(slug);
  };

  const handleYamlFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // permite re-seleccionar el mismo archivo
    if (!file) return;
    const text = await file.text();
    setYamlText(text);
    setYamlFileName(file.name);
    if (!name.trim()) setName(file.name.replace(/\.ya?ml$/i, ""));
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      await onSubmit(
        yamlMode
          ? { name: name.trim(), yaml: yamlText }
          : { name: name.trim(), templateSlug }
      );
      resetForm();
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (value: boolean) => {
    if (!value) resetForm();
    onOpenChange(value);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-lg p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="workflow-name">{t("nameLabel")}</Label>
            <Input
              id="workflow-name"
              placeholder={t("namePlaceholder")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
              }}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label>{t("typeLabel")}</Label>
            <div className="grid grid-cols-1 gap-2">
              {starterRecipes.map((recipe) => {
                const isSelected = !yamlMode && templateSlug === recipe.slug;
                return (
                  <button
                    key={recipe.slug ?? "standard-extraction"}
                    type="button"
                    onClick={() => selectRecipe(recipe.slug)}
                    className={`flex cursor-pointer flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-colors ${
                      isSelected
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30 hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <recipe.icon
                        className={`h-4 w-4 ${isSelected ? "text-primary" : "text-muted-foreground"}`}
                      />
                      <span className="text-sm font-medium">
                        {recipe.label}
                      </span>
                    </div>
                    <span className="text-xs leading-tight text-muted-foreground">
                      {recipe.description}
                    </span>
                  </button>
                );
              })}

              <button
                type="button"
                onClick={() => setYamlMode(true)}
                className={`flex cursor-pointer flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-colors ${
                  yamlMode
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/30 hover:bg-muted/50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileCode
                    className={`h-4 w-4 ${yamlMode ? "text-primary" : "text-muted-foreground"}`}
                  />
                  <span className="text-sm font-medium">{t("fromYaml")}</span>
                </div>
                <span className="text-xs leading-tight text-muted-foreground">
                  {t("fromYamlDescription")}
                </span>
              </button>
            </div>

            {yamlMode && (
              <div className="space-y-2 pt-1">
                <input
                  id="yaml-file"
                  type="file"
                  accept=".yml,.yaml,application/x-yaml,text/yaml"
                  className="sr-only"
                  onChange={handleYamlFile}
                />
                <Label
                  htmlFor="yaml-file"
                  className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-sm font-normal transition-colors hover:border-primary/40 hover:bg-muted/50"
                >
                  <Upload className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span
                    className={
                      yamlFileName ? "font-medium" : "text-muted-foreground"
                    }
                  >
                    {yamlFileName ?? t("yamlFileButton")}
                  </span>
                </Label>
                <p className="text-xs leading-tight text-muted-foreground">
                  {t("yamlFileHint")}
                </p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isSubmitting}
          >
            {t("cancel")}
          </Button>
          <ActionButton
            onClick={handleSubmit}
            disabled={!canSubmit}
            loading={isSubmitting}
          >
            {t("submit")}
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
